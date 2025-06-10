from abc import ABC, abstractmethod
from functools import partial
from typing import Generic, TypeVar, cast

import numpy as np
from numpy.typing import NDArray

from libecalc.common.errors.exceptions import EcalcError, IllegalStateException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.process.compressor.core.base import CompressorModel
from libecalc.domain.process.compressor.core.results import (
    CompressorTrainResultSingleTimeStep,
    CompressorTrainStageResultSingleTimeStep,
)
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.compressor.core.train.utils.common import (
    EPSILON,
    POWER_CALCULATION_TOLERANCE,
    PRESSURE_CALCULATION_TOLERANCE,
    RATE_CALCULATION_TOLERANCE,
)
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import (
    find_root,
    maximize_x_given_boolean_condition_function,
)
from libecalc.domain.process.compressor.core.utils import map_compressor_train_stage_to_domain
from libecalc.domain.process.compressor.dto.train import CompressorTrain as CompressorTrainDTO
from libecalc.domain.process.compressor.dto.train import SingleSpeedCompressorTrain as SingleSpeedCompressorTrainDTO
from libecalc.domain.process.compressor.dto.train import (
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.domain.process.core import INVALID_INPUT, ModelInputFailureStatus, validate_model_input
from libecalc.domain.process.core.results import CompressorTrainResult
from libecalc.domain.process.core.results.compressor import TargetPressureStatus
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.fluid_stream import ProcessConditions
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface

TModel = TypeVar("TModel", bound=CompressorTrainDTO)
INVALID_MAX_RATE = INVALID_INPUT


class CompressorTrainModel(CompressorModel, ABC, Generic[TModel]):
    """Base model for compressor trains with common shaft."""

    def __init__(self, data_transfer_object: TModel, fluid_factory: FluidFactoryInterface):
        self.data_transfer_object = data_transfer_object
        self.fluid_factory = fluid_factory
        self.stages = [map_compressor_train_stage_to_domain(stage_dto) for stage_dto in data_transfer_object.stages]
        self.maximum_power = data_transfer_object.maximum_power

    @property
    def number_of_compressor_stages(self) -> int:
        return len(self.stages)

    @property
    def minimum_speed(self) -> float:
        """Determine the minimum speed of the compressor train if variable speed. Otherwise, it doesn't make sense."""
        return max([stage.compressor_chart.minimum_speed for stage in self.stages])

    @property
    def maximum_speed(self) -> float:
        """Determine the maximum speed of the compressor train if variable speed. Otherwise it doesn't make sense."""
        return min([stage.compressor_chart.maximum_speed for stage in self.stages])

    @property
    def pressure_control(self) -> FixedSpeedPressureControl | None:
        return self.data_transfer_object.pressure_control

    @property
    def maximum_discharge_pressure(self) -> float | None:
        if isinstance(self.data_transfer_object, SingleSpeedCompressorTrainDTO):
            return self.data_transfer_object.maximum_discharge_pressure
        else:
            return None

    def evaluate(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        intermediate_pressure: NDArray[np.float64] | None = None,
    ) -> CompressorTrainResult:
        """
        Evaluate the compressor train's total power based on rate, suction pressure, and discharge pressure.

        Preprocessing:
            - Set total power to 0.0 for zero or negative rates.
            - Set total power to 0.0 for zero pressure increase.
            - Calculate power for valid points where discharge pressure is larger than suction pressure.

        Note:
            - For multiple streams, `rate` can be indexed as `rate[stream, period]`.
            - Example: For two streams and three periods, the array is structured as
              `np.array([[t1, t2, t3], [t1, t2, t3]])`.
            - During preprocessing, compare rates per timestep using methods like `np.min(rate, axis=0)`.

        Args:
            rate (NDArray[np.float64]): Rate in [Sm3/day] per timestep and per stream.
                For all models except the multiple streams model, only one stream is used.
            suction_pressure (NDArray[np.float64]): Suction pressure in [bara].
            discharge_pressure (NDArray[np.float64]): Discharge pressure in [bara].
            intermediate_pressure (NDArray[np.float64] | None): Intermediate pressure in [bara], or None.

        Returns:
            CompressorTrainResult: The result of the compressor train evaluation.
        """
        logger.debug(
            f"Evaluating {type(self).__name__} given suction pressure, discharge pressure, "
            "and potential inter-stage pressure."
        )
        rate, suction_pressure, discharge_pressure, intermediate_pressure, input_failure_status = validate_model_input(
            rate=rate,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            intermediate_pressure=intermediate_pressure,
        )
        train_results = []
        for rate_value, suction_pressure_value, intermediate_pressure_value, discharge_pressure_value in zip(
            np.transpose(rate),
            suction_pressure,
            intermediate_pressure if intermediate_pressure is not None else [None] * len(suction_pressure),
            discharge_pressure,
        ):
            if isinstance(rate_value, np.ndarray):
                rate_value = list(rate_value)
                constraints_rate = rate_value[0]
                constraints_stream_rates = rate_value
            else:
                constraints_rate = rate_value
                constraints_stream_rates = None
            evaluation_constraints = CompressorTrainEvaluationInput(
                rate=constraints_rate,
                suction_pressure=suction_pressure_value,
                discharge_pressure=discharge_pressure_value,
                interstage_pressure=intermediate_pressure_value,
                stream_rates=constraints_stream_rates,
            )
            train_results.append(self.evaluate_given_constraints(constraints=evaluation_constraints))

        power_mw = np.array([result.power_megawatt for result in train_results])
        power_mw_adjusted = np.where(
            power_mw > 0,
            power_mw * self.data_transfer_object.energy_usage_adjustment_factor
            + self.data_transfer_object.energy_usage_adjustment_constant,
            power_mw,
        )

        max_standard_rate = np.full_like(suction_pressure, fill_value=INVALID_MAX_RATE, dtype=float)
        if self.data_transfer_object.calculate_max_rate:
            # calculate max standard rate for time steps with valid input
            valid_indices = [
                i
                for (i, failure_status) in enumerate(input_failure_status)
                if failure_status == ModelInputFailureStatus.NO_FAILURE
            ]
            if isinstance(self.data_transfer_object, VariableSpeedCompressorTrainMultipleStreamsAndPressures):
                max_standard_rate_for_valid_indices = self.get_max_standard_rate(
                    suction_pressures=suction_pressure[valid_indices],
                    discharge_pressures=discharge_pressure[valid_indices],
                    stream_rates=rate[:, valid_indices],
                )
                max_standard_rate[valid_indices] = max_standard_rate_for_valid_indices
            else:
                max_standard_rate_for_valid_indices = self.get_max_standard_rate(
                    suction_pressures=suction_pressure[valid_indices],
                    discharge_pressures=discharge_pressure[valid_indices],
                )
                max_standard_rate[valid_indices] = max_standard_rate_for_valid_indices

        (
            inlet_stream_condition,
            outlet_stream_condition,
            stage_results,
        ) = CompressorTrainResultSingleTimeStep.from_result_list_to_dto(
            result_list=train_results,
            compressor_charts=[stage.compressor_chart.data_transfer_object for stage in self.stages],  # type: ignore[misc]
        )

        return CompressorTrainResult(
            inlet_stream_condition=inlet_stream_condition,
            outlet_stream_condition=outlet_stream_condition,
            energy_usage=list(power_mw_adjusted),
            energy_usage_unit=Unit.MEGA_WATT,
            power=list(power_mw_adjusted),
            power_unit=Unit.MEGA_WATT,
            rate_sm3_day=cast(list, rate.tolist()),
            max_standard_rate=cast(list, max_standard_rate.tolist()),
            stage_results=stage_results,
            failure_status=[
                input_failure_status[i]  # type: ignore[misc]
                if input_failure_status[i] is not ModelInputFailureStatus.NO_FAILURE
                else t.failure_status
                for i, t in enumerate(train_results)
            ],
        )

    @abstractmethod
    def evaluate_given_constraints(
        self, constraints: CompressorTrainEvaluationInput
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the compressor model based on the set constraints.

        The constraints can be:
            * Rate (train inlet)
            * Additional rates for each stream (if multiple streams)
            * Suction pressure (train inlet)
            * Discharge pressure (train outlet)
            * Intermediate pressure (inter-stage)
            * Speed (if variable speed)

        The evaluation is done for a single time step.

        Return:
            CompressorTrainResultSingleTimeStep: The result of the compressor train evaluation.
        """
        ...

    def calculate_pressure_ratios_per_stage(
        self,
        suction_pressure: NDArray[np.float64] | float,
        discharge_pressure: NDArray[np.float64] | float,
    ) -> NDArray[np.float64] | float:
        """Given the number of compressors, and based on the assumption that all compressors have the same pressure ratio,
        compute all pressure ratios.
        """
        if len(self.stages) < 1:
            raise ValueError("Can't compute pressure rations when no compressor stages are defined.")
        if isinstance(suction_pressure, np.ndarray):
            pressure_ratios = np.divide(
                discharge_pressure, suction_pressure, out=np.ones_like(suction_pressure), where=suction_pressure != 0
            )
            return pressure_ratios ** (1.0 / len(self.stages))
        else:
            pressure_ratios = discharge_pressure / suction_pressure
            return pressure_ratios ** (1.0 / len(self.stages))

    def check_target_pressures(
        self,
        constraints: CompressorTrainEvaluationInput,
        results: CompressorTrainResultSingleTimeStep | list[CompressorTrainStageResultSingleTimeStep],
    ) -> TargetPressureStatus:
        """Check to see how the calculated pressures compare to the required pressures
        Args:
            constraints: The evaluation constraints given to the evaluation
            results: The results from the compressor train evaluation

        Returns:
            TargetPressureStatus: The status of the target pressures
        """
        if isinstance(results, list):
            train_suction_pressure = results[0].inlet_pressure
            calculated_discharge_pressure = results[-1].discharge_pressure
            calculated_intermediate_pressure = None
            stage_suction_pressure = results[0].inlet_pressure
        else:
            train_suction_pressure = results.suction_pressure
            calculated_discharge_pressure = results.discharge_pressure
            stage_suction_pressure = results.stage_results[0].inlet_stream.pressure_bara
            if constraints.stream_rates is not None:
                calculated_intermediate_pressure = (
                    results.stage_results[
                        self.data_transfer_object.stage_number_interstage_pressure - 1
                    ].discharge_pressure
                    if self.data_transfer_object.stage_number_interstage_pressure is not None
                    else None
                )
            else:
                calculated_intermediate_pressure = None
        if stage_suction_pressure is not None:
            if (stage_suction_pressure / train_suction_pressure) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.ABOVE_TARGET_SUCTION_PRESSURE
        if constraints.discharge_pressure is not None:
            if (calculated_discharge_pressure / constraints.discharge_pressure) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.ABOVE_TARGET_DISCHARGE_PRESSURE
            if (constraints.discharge_pressure / calculated_discharge_pressure) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.BELOW_TARGET_DISCHARGE_PRESSURE
        if constraints.interstage_pressure is not None and calculated_intermediate_pressure is not None:
            if (
                calculated_intermediate_pressure / constraints.interstage_pressure
            ) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.ABOVE_TARGET_INTERMEDIATE_PRESSURE
            if (
                constraints.interstage_pressure / calculated_intermediate_pressure
            ) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.BELOW_TARGET_INTERMEDIATE_PRESSURE

        return TargetPressureStatus.TARGET_PRESSURES_MET

    def evaluate_with_pressure_control_given_constraints(
        self, constraints: CompressorTrainEvaluationInput
    ) -> CompressorTrainResultSingleTimeStep:
        """

        Args:
            constraints:

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the compressor train evaluation.
        """
        if self.pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
            train_result = self._evaluate_train_with_downstream_choking(
                constraints=constraints,
            )
        elif self.pressure_control == FixedSpeedPressureControl.UPSTREAM_CHOKE:
            train_result = self._evaluate_train_with_upstream_choking(
                constraints=constraints,
            )
        elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE:
            train_result = self._evaluate_train_with_individual_asv_rate(
                constraints=constraints,
            )
        elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE:
            train_result = self._evaluate_train_with_individual_asv_pressure(
                constraints=constraints,
            )
        elif self.pressure_control == FixedSpeedPressureControl.COMMON_ASV:
            train_result = self._evaluate_train_with_common_asv(
                constraints=constraints,
            )
        else:
            raise ValueError(f"Pressure control {self.pressure_control} not supported")

        return train_result

    def _evaluate_train_with_downstream_choking(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate a single-speed compressor train's total power given mass rate, suction pressure, and discharge pressure.

        This method assumes that the discharge pressure is controlled to meet the target using a downstream choke valve.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        train_result = self.calculate_compressor_train(
            constraints=constraints,
        )

        if self.maximum_discharge_pressure is not None:
            if train_result.discharge_pressure * (1 + PRESSURE_CALCULATION_TOLERANCE) > self.maximum_discharge_pressure:
                new_train_result = self._evaluate_train_with_upstream_choking(
                    constraints=constraints.create_conditions_with_new_input(
                        new_discharge_pressure=self.maximum_discharge_pressure,
                    ),
                )
                train_result.stage_results = new_train_result.stage_results
                train_result.outlet_stream = new_train_result.outlet_stream
                train_result.target_pressure_status = self.check_target_pressures(
                    constraints=constraints,
                    results=train_result,
                )

        if train_result.target_pressure_status == TargetPressureStatus.ABOVE_TARGET_DISCHARGE_PRESSURE:
            # At this point, discharge_pressure must be set since we're checking target pressures
            assert constraints.discharge_pressure is not None
            train_result.outlet_stream = train_result.outlet_stream.create_stream_with_new_conditions(
                conditions=ProcessConditions(
                    pressure_bara=constraints.discharge_pressure,
                    temperature_kelvin=train_result.outlet_stream.temperature_kelvin,
                )
            )
            train_result.target_pressure_status = self.check_target_pressures(
                constraints=constraints,
                results=train_result,
            )

        return train_result

    def _evaluate_train_with_upstream_choking(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the compressor train's total power assuming upstream choking is used to control suction pressure.

        This method iteratively adjusts the suction pressure to achieve the target discharge pressure.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        assert constraints.rate is not None
        assert constraints.suction_pressure is not None

        train_inlet_stream = self.fluid_factory.create_stream_from_standard_rate(
            pressure_bara=constraints.suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
            standard_rate_m3_per_day=constraints.rate,
        )

        def _calculate_train_result_given_inlet_pressure(
            inlet_pressure: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Note that we use outside variables for clarity and to avoid class instances."""
            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_suction_pressure=inlet_pressure,
                ),
            )

        # This method requires discharge_pressure to be set
        assert constraints.discharge_pressure is not None
        target_discharge_pressure = constraints.discharge_pressure

        result_inlet_pressure = find_root(
            lower_bound=EPSILON + self.stages[0].pressure_drop_ahead_of_stage,  # type: ignore
            upper_bound=target_discharge_pressure,
            func=lambda x: _calculate_train_result_given_inlet_pressure(inlet_pressure=x).discharge_pressure
            - target_discharge_pressure,
        )

        train_result = _calculate_train_result_given_inlet_pressure(inlet_pressure=result_inlet_pressure)
        train_result.inlet_stream = train_inlet_stream

        train_result.target_pressure_status = self.check_target_pressures(
            constraints=constraints,
            results=train_result,
        )
        return train_result

    def _evaluate_train_with_individual_asv_rate(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the total power of a single-speed compressor train given suction pressure, discharge pressure,
        and a minimum mass rate.

        This method assumes that the discharge pressure is controlled to meet the target using anti-surge valves (ASVs).
        The ASVs increase the net rate until the head is reduced enough in each compressor stage to meet the target
        discharge pressure. For multiple compressor stages, the ASV recirculation is distributed proportionally across
        all stages, ensuring the same ASV fraction is applied to each stage.

        The ASV fraction that results in the target discharge pressure is found using a Newton iteration

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """

        def _calculate_train_result_given_asv_rate_margin(
            asv_rate_fraction: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Note that we use outside variables for clarity and to avoid class instances."""
            return self.calculate_compressor_train(
                constraints=constraints,
                asv_rate_fraction=asv_rate_fraction,
            )

        minimum_asv_fraction = 0.0
        maximum_asv_fraction = 1.0
        train_result_for_minimum_asv_rate_fraction = _calculate_train_result_given_asv_rate_margin(
            asv_rate_fraction=minimum_asv_fraction
        )
        if (train_result_for_minimum_asv_rate_fraction.chart_area_status == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE) or (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure > train_result_for_minimum_asv_rate_fraction.discharge_pressure
        ):
            return train_result_for_minimum_asv_rate_fraction
        train_result_for_maximum_asv_rate_fraction = _calculate_train_result_given_asv_rate_margin(
            asv_rate_fraction=maximum_asv_fraction
        )
        if (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure < train_result_for_maximum_asv_rate_fraction.discharge_pressure
        ):
            return train_result_for_maximum_asv_rate_fraction

        # This method requires discharge_pressure for the Newton iteration
        assert constraints.discharge_pressure is not None
        target_discharge_pressure = constraints.discharge_pressure

        result_asv_rate_margin = find_root(
            lower_bound=0.0,
            upper_bound=1.0,
            func=lambda x: _calculate_train_result_given_asv_rate_margin(asv_rate_fraction=x).discharge_pressure
            - target_discharge_pressure,
        )
        # This mass rate, is the mass rate to use as mass rate after asv for each stage,
        # thus the asv in each stage should be set to correspond to this mass rate
        return _calculate_train_result_given_asv_rate_margin(asv_rate_fraction=result_asv_rate_margin)

    def _evaluate_train_with_individual_asv_pressure(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the compressor train's total power using individual ASV pressure control.

        This method ensures that the pressure ratio (discharge pressure / suction pressure) is equal across all compressors
        in the train. ASVs are independently adjusted to achieve the required discharge pressure for each compressor.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        # This method requires both suction and discharge pressure to be set
        assert constraints.suction_pressure is not None
        assert constraints.discharge_pressure is not None

        inlet_stream_train = self.fluid_factory.create_stream_from_standard_rate(
            pressure_bara=constraints.suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
            standard_rate_m3_per_day=constraints.rate,  # type: ignore[arg-type]
        )
        pressure_ratio_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=constraints.suction_pressure,
            discharge_pressure=constraints.discharge_pressure,
        )
        inlet_stream_stage = inlet_stream_train
        stage_results = []
        for stage in self.stages:
            outlet_pressure_for_stage = inlet_stream_stage.pressure_bara * pressure_ratio_per_stage
            stage_result = stage.evaluate_given_speed_and_target_discharge_pressure(
                target_discharge_pressure=outlet_pressure_for_stage,  # type: ignore[arg-type]
                inlet_stream_stage=inlet_stream_stage,
            )
            inlet_stream_stage = stage_result.outlet_stream
            stage_results.append(stage_result)

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            constraints=constraints,
            results=stage_results,
        )
        return CompressorTrainResultSingleTimeStep(
            inlet_stream=inlet_stream_train,
            outlet_stream=stage_result.outlet_stream,
            speed=float("nan"),
            stage_results=stage_results,
            target_pressure_status=target_pressure_status,
        )

    def _evaluate_train_with_common_asv(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the total power of a single-speed compressor train given suction pressure, discharge pressure,
        and a constant mass rate.

        This method assumes that the discharge pressure is controlled to meet the target using anti-surge valves (ASVs).
        The ASVs increase the net rate until the head is reduced enough in each compressor stage to meet the target
        discharge pressure. For multiple compressor stages, the ASV recirculation is applied over the entire train,
        ensuring a constant mass rate across all stages.

        A Newton iteration is used to find the mass rate that results in the target discharge pressure.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        minimum_mass_rate_kg_per_hour = self.fluid_factory.standard_rate_to_mass_rate(
            standard_rate_m3_per_day=constraints.rate,  # type: ignore[arg-type]
        )
        # Iterate on rate until pressures are met
        density_train_inlet_fluid = self.fluid_factory.create_thermo_system(
            pressure_bara=constraints.suction_pressure,  # type: ignore[arg-type]
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        ).density

        def _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self.fluid_factory.mass_rate_to_standard_rate(mass_rate_kg_per_h=mass_rate_kg_per_hour),  # type: ignore[arg-type]
                ),
            )

        def _calculate_train_result_given_additional_mass_rate(
            additional_mass_rate_kg_per_hour: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_compressor_train(
                constraints=constraints,
                asv_additional_mass_rate=additional_mass_rate_kg_per_hour,
            )

        # outer bounds for minimum and maximum mass rate without individual recirculation on stages will be the
        # minimum and maximum mass rate for the first stage, adjusted for the volume entering the first stage
        minimum_mass_rate = max(
            minimum_mass_rate_kg_per_hour,
            self.stages[0].compressor_chart.minimum_rate * density_train_inlet_fluid,
        )  # type: ignore[type-var]
        # note: we subtract EPSILON to avoid floating point issues causing the maximum mass rate to exceed chart area maximum rate after round-trip conversion (mass rate -> standard rat -> mass rate)
        maximum_mass_rate = self.stages[0].compressor_chart.maximum_rate * density_train_inlet_fluid * (1 - EPSILON)

        # if the minimum_mass_rate_kg_per_hour(i.e. before increasing rate with recirculation to lower pressure)
        # is already larger than the maximum mass rate, there is no need for optimization - just add result
        # with minimum_mass_rate_kg_per_hour (which will fail with above maximum flow rate)
        if minimum_mass_rate_kg_per_hour > maximum_mass_rate:
            return _calculate_train_result_given_mass_rate(mass_rate_kg_per_hour=minimum_mass_rate_kg_per_hour)  # type: ignore[arg-type]

        train_result_for_minimum_mass_rate = _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour=float(minimum_mass_rate)
        )
        train_result_for_maximum_mass_rate = _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour=float(maximum_mass_rate)
        )
        if train_result_for_minimum_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
            if not train_result_for_maximum_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
                # find the maximum additional_mass_rate that gives train_results.is_valid
                maximum_mass_rate = maximize_x_given_boolean_condition_function(
                    x_min=0.0,
                    x_max=maximum_mass_rate,
                    bool_func=lambda x: _calculate_train_result_given_mass_rate(
                        mass_rate_kg_per_hour=x
                    ).mass_rate_asv_corrected_is_constant_for_stages,
                    convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
                train_result_for_maximum_mass_rate = _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=maximum_mass_rate
                )
        elif train_result_for_maximum_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
            # find the minimum additional_mass_rate that gives all points internal
            minimum_mass_rate = -maximize_x_given_boolean_condition_function(
                x_min=-maximum_mass_rate,
                x_max=-minimum_mass_rate,  # type: ignore[arg-type]
                bool_func=lambda x: _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=-x
                ).mass_rate_asv_corrected_is_constant_for_stages,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            train_result_for_minimum_mass_rate = _calculate_train_result_given_mass_rate(
                mass_rate_kg_per_hour=minimum_mass_rate
            )
        else:
            # Try to find a point with all internal points. Testing 10 evenly spaced additional mass rates.
            # If none of those give a valid results, the compressor train is poorly designed...
            inc = 0.1
            train_result_for_mass_rate = _calculate_train_result_given_mass_rate(
                mass_rate_kg_per_hour=minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)  # type: ignore[arg-type]
            )
            while not train_result_for_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
                inc += 0.1
                if inc >= 1:
                    logger.error("Single speed train with Common ASV pressure control has no solution!")
                train_result_for_mass_rate = _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)  # type: ignore[arg-type]
                )

            # found one solution, now find min and max
            minimum_mass_rate = -maximize_x_given_boolean_condition_function(
                x_min=-(minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)),  # type: ignore[arg-type]
                x_max=-minimum_mass_rate,  # type: ignore[arg-type]
                bool_func=lambda x: _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=-x
                ).mass_rate_asv_corrected_is_constant_for_stages,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            maximum_mass_rate = maximize_x_given_boolean_condition_function(
                x_min=(minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)),
                x_max=maximum_mass_rate,
                bool_func=lambda x: _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=x
                ).mass_rate_asv_corrected_is_constant_for_stages,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            train_result_for_minimum_mass_rate = _calculate_train_result_given_mass_rate(
                mass_rate_kg_per_hour=minimum_mass_rate
            )
            train_result_for_maximum_mass_rate = _calculate_train_result_given_mass_rate(
                mass_rate_kg_per_hour=maximum_mass_rate
            )
        if (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure > train_result_for_minimum_mass_rate.discharge_pressure
        ):
            # will never reach target pressure, too high
            return train_result_for_minimum_mass_rate
        if (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure < train_result_for_maximum_mass_rate.discharge_pressure
        ):
            # will never reach target pressure, too low
            return train_result_for_maximum_mass_rate

        # This method requires discharge_pressure for the Newton iteration
        assert constraints.discharge_pressure is not None
        target_discharge_pressure = constraints.discharge_pressure

        result_mass_rate = find_root(
            lower_bound=minimum_mass_rate,  # type: ignore[arg-type]
            upper_bound=maximum_mass_rate,
            func=lambda x: _calculate_train_result_given_mass_rate(mass_rate_kg_per_hour=x).discharge_pressure
            - target_discharge_pressure,
        )
        # This mass rate is the mass rate to use as mass rate after asv for each stage,
        # thus the asv in each stage should be set to correspond to this mass rate
        return _calculate_train_result_given_additional_mass_rate(
            additional_mass_rate_kg_per_hour=(result_mass_rate - minimum_mass_rate_kg_per_hour)  # type: ignore[arg-type]
        )

    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
        stream_rates: NDArray[np.float64] | None = None,
    ) -> NDArray[np.float64]:
        """
        Calculate the maximum standard volume rate [Sm3/day] that the compressor train can operate at.

        This method determines the maximum rate by evaluating the compressor train's capacity
        based on the given suction and discharge pressures. It considers the compressor's
        operational constraints, including the maximum allowable power and the compressor chart limits.

        Args:
            suction_pressures (float): The suction pressures in bara for each time step.
            discharge_pressures (float): The discharge pressures in bara for each time step.

        Returns:
            NDArray[np.float64]: An array of maximum standard rates for each time step.
            If the maximum rate cannot be determined, it returns INVALID_MAX_RATE for that time step.
        """

        max_standard_rate = np.full_like(suction_pressures, fill_value=INVALID_MAX_RATE, dtype=float)
        for i, (suction_pressure_value, discharge_pressure_value) in enumerate(
            zip(
                suction_pressures,
                discharge_pressures,
            )
        ):
            if stream_rates is not None:
                constraints = CompressorTrainEvaluationInput(
                    suction_pressure=suction_pressure_value,
                    discharge_pressure=discharge_pressure_value,
                    rate=stream_rates[0],
                    stream_rates=stream_rates,  # type: ignore[arg-type]
                )
            else:
                constraints = CompressorTrainEvaluationInput(
                    suction_pressure=suction_pressure_value,
                    discharge_pressure=discharge_pressure_value,
                    rate=EPSILON,
                )
            try:
                max_standard_rate[i] = self._get_max_std_rate_single_timestep(
                    constraints=constraints,
                )
            except EcalcError as e:
                logger.exception(e)
                max_standard_rate[i] = float("nan")

        return max_standard_rate

    def find_shaft_speed_given_constraints(
        self,
        constraints: CompressorTrainEvaluationInput,
        lower_bound_for_speed: float | None = None,
        upper_bound_for_speed: float | None = None,
    ) -> float:
        """Calculate needed shaft speed to get desired outlet pressure

        Run compressor train forward model with inlet conditions and speed, and iterate on shaft speed until discharge
        pressure meets requested discharge pressure.

        Iteration (using brenth method) to find speed to meet requested discharge pressure

        The upper and lower bounds for the speed can be set, which is useful for a part of a compressor train that can
        share a common shaft with another part of a compressor train, which has another minimum and maximum speed.

        Iterative problem:
            f(speed) = calculate_compressor_train(speed).discharge_pressure - requested_discharge_pressure = 0
        Starting points for iterative method:
           speed_0 = minimum speed for train, calculate f(speed_0) aka f_0
           speed_1 = maximum speed for train, calculate f(speed_1) aka f_1

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.
            lower_bound_for_speed (float | None): The lower bound for the speed. If None, uses the minimum speed
            upper_bound_for_speed (float | None): The upper bound for the speed. If None, uses the maximum speed
        Returns:
            The speed required to operate at to meet the given constraints. (Bounded by the minimu and maximum speed)

        """
        minimum_speed = (
            lower_bound_for_speed
            if lower_bound_for_speed and lower_bound_for_speed > self.minimum_speed
            else self.minimum_speed
        )
        maximum_speed = (
            upper_bound_for_speed
            if upper_bound_for_speed and upper_bound_for_speed < self.maximum_speed
            else self.maximum_speed
        )
        if constraints.speed is not None:
            return constraints.speed
        if isinstance(self.data_transfer_object, SingleSpeedCompressorTrainDTO):
            return self.data_transfer_object.speed

        def _calculate_compressor_train(_speed: float) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_speed=_speed,
                )
            )

        train_result_for_minimum_speed = _calculate_compressor_train(_speed=minimum_speed)
        train_result_for_maximum_speed = _calculate_compressor_train(_speed=maximum_speed)

        if not train_result_for_maximum_speed.within_capacity:
            # will not find valid result - the rate is above maximum rate, return invalid results at maximum speed
            return maximum_speed
        if not train_result_for_minimum_speed.within_capacity:
            # rate is above maximum rate for minimum speed. Find the lowest minimum speed which gives a valid result
            minimum_speed = -maximize_x_given_boolean_condition_function(
                x_min=-maximum_speed,
                x_max=-minimum_speed,
                bool_func=lambda x: _calculate_compressor_train(_speed=-x).within_capacity,
            )
            train_result_for_minimum_speed = _calculate_compressor_train(_speed=minimum_speed)

        # Solution 1, iterate on speed until target discharge pressure is found
        if (
            constraints.discharge_pressure is not None
            and train_result_for_minimum_speed.discharge_pressure
            <= constraints.discharge_pressure
            <= train_result_for_maximum_speed.discharge_pressure
        ):
            # At this point, discharge_pressure is confirmed to be not None
            target_discharge_pressure = constraints.discharge_pressure
            speed = find_root(
                lower_bound=minimum_speed,
                upper_bound=maximum_speed,
                func=lambda x: _calculate_compressor_train(_speed=x).discharge_pressure - target_discharge_pressure,
            )

            return speed

        # Solution 2, target pressure is too low:
        if (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure < train_result_for_minimum_speed.discharge_pressure
        ):
            return minimum_speed

        # Solution 3, target discharge pressure is too high
        return maximum_speed

    def _get_max_std_rate_single_timestep(
        self,
        constraints: CompressorTrainEvaluationInput,
        allow_asv: bool = False,
    ) -> float:
        """Calculate the max standard rate [Sm3/day] that the compressor train can operate at for a single time step.

        The maximum rate can be found in 3 areas:
            1. The compressor train can't reach the required target pressure regardless of speed
               -> Left of the chart.
            2. The compressor train hits the required outlet pressure on the maximum speed curve
               -> On the max speed curve.
            3. The compressor train hits the required outlet pressure somewhere on the stone wall
               -> On the stone wall (for variable speed charts only)
            4. If the found maximum rate requires power above the maximum power, then rate is reduced
               until the power is within limits.

        This is how we search for the solution:
            1. If the compressor train cannot reach the target pressure regardless of rate and ASV (if allowed). Return 0.
            2. Else if the solution is along the maximum speed curve;
                then we iterate on mass rate along the maximum speed curve to find a solution.
            3. Else if the pressure is too high and pressure control is choking either upstream or downstream,
                then the solution is still on the max speed curve.
            4. Else if the solution is on the "stone wall";
                then we iterate on speed along the "stone wall" to find a solution.
            5. Else if the outlet pressure is still too high is still too low, the pressure points given are not valid.
                We still want to provide a maximum rate number as we do not want the consumer system calculations to fail,
                but rather trigger an infeasible solution at evaluation. Thus - return minimum rate for maximum speed for
                pressure ratios too high, and minimum rate for stone wall (i.e. maximum rate for minimum speed) for pressure
                ratios too low.

        Note: we only have information enough to make the inlet streams. For the outlet streams, we only have
        pressure, the temperature needs to be calculated as part of the process

        Note: We use this method's variable scope within the inner functions.

        Note: In the future:
            We have density_per_stage, that can be used to calculate the inlet actual rate for any stage.
            May be useful to add mass_rate_kg_per_hour to StageResultSingleCalculationPoint.

        Args:
            constraints (CompressorTrainEvaluationInput: The constraints for the evaluation.
            allow_asv:

        Returns:
            Standard volume rate [Sm3/day]

        """
        inlet_stream = self.fluid.get_fluid_stream(
            pressure_bara=constraints.suction_pressure,  # type: ignore[arg-type]
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )
        inlet_density = inlet_stream.density

        def _calculate_train_result(mass_rate: float, speed: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.calculate_compressor_train_given_speed
            where we only pass mass_rate.
            """
            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=mass_rate),  # type: ignore[arg-type]
                    new_speed=speed,
                )
            )

        def _calculate_train_result_given_ps_pd(mass_rate: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.evaluate_given_constraints
            where we only pass mass_rate.
            """
            return self.evaluate_given_constraints(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=mass_rate),  # type: ignore[arg-type]
                )
            )

        def _calculate_train_result_given_speed_at_stone_wall(
            speed: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.calculate_compressor_train.
            Same as above, but mass rate is pinned to the "stone wall" as a function of speed.
            """
            assert not isinstance(self.data_transfer_object, SingleSpeedCompressorTrainDTO)
            _max_valid_mass_rate_at_given_speed = maximize_x_given_boolean_condition_function(
                x_min=self.stages[0].compressor_chart.minimum_rate_as_function_of_speed(speed) * inlet_density,  # or 0?
                x_max=self.stages[0].compressor_chart.maximum_rate_as_function_of_speed(speed) * inlet_density,
                bool_func=lambda x: _calculate_train_result(mass_rate=x, speed=speed).within_capacity,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )

            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self.fluid.mass_rate_to_standard_rate(
                        mass_rate_kg_per_hour=_max_valid_mass_rate_at_given_speed
                    ),  # type: ignore[arg-type]
                    new_speed=speed,
                )
            )

        # Same as the partial functions above, but simpler syntax using partial()
        _calculate_train_result_at_max_speed_given_mass_rate = partial(
            _calculate_train_result, speed=self.maximum_speed
        )

        _calculate_train_result_at_min_speed_given_mass_rate = partial(
            _calculate_train_result, speed=self.minimum_speed
        )

        # Using first stage as absolute (initial) bounds on min and max rate at max speed. Checking validity later.
        min_mass_rate_at_max_speed_first_stage = (
            self.stages[0].compressor_chart.maximum_speed_curve.minimum_rate * inlet_density
        )
        max_mass_rate_at_max_speed_first_stage = (
            self.stages[0].compressor_chart.maximum_speed_curve.maximum_rate * inlet_density
        )
        max_mass_rate_at_min_speed_first_stage = (
            max_mass_rate_at_max_speed_first_stage
            if isinstance(self.data_transfer_object, SingleSpeedCompressorTrainDTO)
            else (
                self.stages[0].compressor_chart.maximum_rate_as_function_of_speed(
                    self.stages[0].compressor_chart.minimum_speed
                )
                * inlet_density
            )
        )

        result_min_mass_rate_at_max_speed_first_stage = _calculate_train_result_at_max_speed_given_mass_rate(
            mass_rate=min_mass_rate_at_max_speed_first_stage
        )
        result_max_mass_rate_at_max_speed_first_stage = _calculate_train_result_at_max_speed_given_mass_rate(
            mass_rate=max_mass_rate_at_max_speed_first_stage
        )
        result_max_mass_rate_at_min_speed_first_stage = _calculate_train_result_at_min_speed_given_mass_rate(
            mass_rate=max_mass_rate_at_min_speed_first_stage
        )

        # Ensure that the minimum mass rate at max speed is valid for the whole train.
        if not result_min_mass_rate_at_max_speed_first_stage.within_capacity:
            if allow_asv:
                min_mass_rate_at_max_speed = EPSILON
                result_min_mass_rate_at_max_speed = _calculate_train_result_at_max_speed_given_mass_rate(
                    mass_rate=min_mass_rate_at_max_speed
                )
                if not result_min_mass_rate_at_max_speed.within_capacity:
                    logger.debug(
                        "There are no valid mass rate for VariableSpeedCompressorTrain."
                        "Infeasible solution. Returning max rate 0.0 (None)."
                    )
                    return 0.0
                max_mass_rate_at_max_speed = maximize_x_given_boolean_condition_function(
                    x_min=EPSILON,
                    x_max=min_mass_rate_at_max_speed_first_stage,
                    bool_func=lambda x: _calculate_train_result_at_max_speed_given_mass_rate(
                        mass_rate=x
                    ).within_capacity,
                    convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
                result_max_mass_rate_at_max_speed = _calculate_train_result_at_max_speed_given_mass_rate(
                    mass_rate=max_mass_rate_at_max_speed
                )
            else:
                logger.debug(
                    "There are no valid common mass rate for VariableSpeedCompressorTrain, and ASV is not allowed."
                    "Infeasible solution. Returning max rate 0.0 (None)."
                )
                return 0.0
        else:
            min_mass_rate_at_max_speed = min_mass_rate_at_max_speed_first_stage
            result_min_mass_rate_at_max_speed = result_min_mass_rate_at_max_speed_first_stage

            # Ensuring that the maximum mass rate at max speed is valid for the whole train.
            if not result_max_mass_rate_at_max_speed_first_stage.within_capacity:
                max_mass_rate_at_max_speed = maximize_x_given_boolean_condition_function(
                    x_min=min_mass_rate_at_max_speed,
                    x_max=max_mass_rate_at_max_speed_first_stage,
                    bool_func=lambda x: _calculate_train_result_at_max_speed_given_mass_rate(
                        mass_rate=x
                    ).within_capacity,
                    convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
                result_max_mass_rate_at_max_speed = _calculate_train_result_at_max_speed_given_mass_rate(
                    mass_rate=max_mass_rate_at_max_speed
                )
            else:
                max_mass_rate_at_max_speed = max_mass_rate_at_max_speed_first_stage
                result_max_mass_rate_at_max_speed = result_max_mass_rate_at_max_speed_first_stage

        # Solution scenario 1. Infeasible. Target pressure is too high.
        if (
            constraints.discharge_pressure is not None
            and result_min_mass_rate_at_max_speed.discharge_pressure < constraints.discharge_pressure
        ):
            return 0.0

        # Solution scenario 2. Solution is at maximum speed curve.
        elif (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure >= result_max_mass_rate_at_max_speed.discharge_pressure
        ):
            """
            Iterating along max speed curve for first stage.
            """
            target_discharge_pressure = constraints.discharge_pressure
            result_mass_rate = find_root(
                lower_bound=min_mass_rate_at_max_speed,
                upper_bound=max_mass_rate_at_max_speed,
                func=lambda x: _calculate_train_result_at_max_speed_given_mass_rate(mass_rate=x).discharge_pressure
                - target_discharge_pressure,
                relative_convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            rate_to_return = result_mass_rate * (1 - RATE_CALCULATION_TOLERANCE)

        # Solution 3: If solution not found along max speed curve, and pressure control is downstream choke, we should
        # run at max_mass_rate, but using the defined pressure control.
        elif self.data_transfer_object.pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
            rate_to_return = max_mass_rate_at_max_speed * (1 - RATE_CALCULATION_TOLERANCE)

        # if pressure control is upstream choke, we find the new maximum rate with the reduced inlet pressure
        elif self.data_transfer_object.pressure_control == FixedSpeedPressureControl.UPSTREAM_CHOKE:
            rate_to_return = maximize_x_given_boolean_condition_function(
                x_min=0,
                x_max=max_mass_rate_at_max_speed_first_stage,
                bool_func=lambda x: _calculate_train_result_given_ps_pd(mass_rate=x).within_capacity,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )

        # Solution scenario 4. Solution at the "Stone wall".
        elif not isinstance(self.data_transfer_object, SingleSpeedCompressorTrainDTO):
            # Ensuring that the maximum mass rate at min speed is valid for the whole train.
            if not result_max_mass_rate_at_min_speed_first_stage.within_capacity:
                max_mass_rate_at_min_speed = maximize_x_given_boolean_condition_function(
                    x_min=EPSILON,
                    x_max=max_mass_rate_at_min_speed_first_stage,
                    bool_func=lambda x: _calculate_train_result_at_min_speed_given_mass_rate(
                        mass_rate=x
                    ).within_capacity,
                )
                result_max_mass_rate_at_min_speed = _calculate_train_result_at_min_speed_given_mass_rate(
                    mass_rate=max_mass_rate_at_min_speed
                )
            else:
                # max_mass_rate_at_min_speed = max_mass_rate_at_max_speed_first_stage
                result_max_mass_rate_at_min_speed = result_max_mass_rate_at_min_speed_first_stage

            if (
                constraints.discharge_pressure is not None
                and result_max_mass_rate_at_max_speed.discharge_pressure
                >= constraints.discharge_pressure
                >= result_max_mass_rate_at_min_speed.discharge_pressure
            ):
                # iterate along stone wall until target discharge pressure is reached
                target_discharge_pressure = constraints.discharge_pressure
                result_speed = find_root(
                    lower_bound=self.minimum_speed,
                    upper_bound=self.maximum_speed,
                    func=lambda x: _calculate_train_result_given_speed_at_stone_wall(speed=x).discharge_pressure
                    - target_discharge_pressure,
                )
                compressor_train_result = _calculate_train_result_given_speed_at_stone_wall(speed=result_speed)

                rate_to_return = compressor_train_result.mass_rate_kg_per_hour * (1 - RATE_CALCULATION_TOLERANCE)

            # Solution scenario 5. Too high pressure even at min speed and max flow rate.
            elif (
                constraints.discharge_pressure is not None
                and result_max_mass_rate_at_min_speed.discharge_pressure > constraints.discharge_pressure
            ):
                return 0.0
            else:
                msg = "You should not end up here. Please contact eCalc support."
                logger.exception(msg)
                raise IllegalStateException(msg)
        else:
            return 0.0

        # Check that rate_to_return, suction_pressure and discharge_pressure does not require too much power.
        # If so, reduce rate such that power comes below maximum power
        if not self.data_transfer_object.maximum_power:
            return self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=rate_to_return)
        elif (
            self.evaluate_given_constraints(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=rate_to_return),  # type: ignore[arg-type]
                )
            ).power_megawatt
            > self.data_transfer_object.maximum_power
        ):
            maximum_power = float(self.data_transfer_object.maximum_power)
            # check if minimum_rate gives too high power consumption
            result_with_minimum_rate = self.evaluate_given_constraints(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=EPSILON,
                )
            )
            if result_with_minimum_rate.power_megawatt > maximum_power:
                return 0.0  # can't find solution
            else:
                # iterate between rate with minimum power, and the previously found rate to return, to find the
                # maximum rate that gives power consumption below maximum power
                return self.fluid.mass_rate_to_standard_rate(
                    mass_rate_kg_per_hour=find_root(
                        lower_bound=result_with_minimum_rate.stage_results[0].mass_rate_asv_corrected_kg_per_hour,
                        upper_bound=rate_to_return,
                        func=lambda x: self.evaluate_given_constraints(
                            constraints=constraints.create_conditions_with_new_input(
                                new_rate=self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=x),  # type: ignore[arg-type]
                            )
                        ).power_megawatt
                        - maximum_power * (1 - POWER_CALCULATION_TOLERANCE),
                        relative_convergence_tolerance=1e-3,
                        maximum_number_of_iterations=20,
                    )
                )
        else:
            # maximum power defined, but found rate is below maximum power
            return self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=rate_to_return)

    def calculate_compressor_train(
        self,
        constraints: CompressorTrainEvaluationInput,
        asv_rate_fraction: float = 0.0,
        asv_additional_mass_rate: float = 0.0,
    ) -> CompressorTrainResultSingleTimeStep:
        """Calculate compressor train result given inlet conditions and speed

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.
            asv_rate_fraction:
            asv_additional_mass_rate:

        Returns:
            results including conditions and calculations for each stage and power.

        """
        if constraints.rate is None or constraints.suction_pressure is None:
            raise EcalcError(
                title="Missing required parameters",
                message="Compressor train calculation requires rate and suction pressure to be set.",
            )
        # Initialize stream at inlet of first compressor stage using fluid properties and inlet conditions
        train_inlet_stream = self.fluid.get_fluid_stream(
            pressure_bara=constraints.suction_pressure - self.stages[0].pressure_drop_ahead_of_stage,  # type: ignore[operator]
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )
        mass_rate_kg_per_hour = self.fluid.standard_rate_to_mass_rate(standard_rates=constraints.rate)
        stage_results: list[CompressorTrainStageResultSingleTimeStep] = []
        outlet_stream = train_inlet_stream
        for stage in self.stages:
            inlet_stream = outlet_stream
            stage_result = stage.evaluate(
                inlet_stream_stage=inlet_stream,
                speed=constraints.speed,
                mass_rate_kg_per_hour=mass_rate_kg_per_hour,  # type: ignore[arg-type]
                asv_rate_fraction=asv_rate_fraction,
                asv_additional_mass_rate=asv_additional_mass_rate,
            )
            stage_results.append(stage_result)

            # We need to recreate the domain object from the result object. This needs cleaning up.
            outlet_stream = inlet_stream.set_new_pressure_and_temperature(
                new_pressure_bara=stage_result.outlet_stream.pressure_bara,
                new_temperature_kelvin=stage_result.outlet_stream.temperature_kelvin,
            )

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            constraints=constraints,
            results=stage_results,
        )

        return CompressorTrainResultSingleTimeStep(
            inlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=train_inlet_stream),
            outlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=outlet_stream),
            stage_results=stage_results,
            speed=constraints.speed if constraints.speed is not None else float("nan"),
            above_maximum_power=sum([stage_result.power_megawatt for stage_result in stage_results])
            > self.maximum_power
            if self.maximum_power
            else False,
            target_pressure_status=target_pressure_status,
        )

    def evaluate_given_constraints(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate a single-speed compressor train total power given evaluation input. The input must contain rate
        and suction pressure and discharge pressure, the pressure control will be invoked
        to reach the target discharge pressure.

        The evaluation varies depending on the chosen pressure control mechanism.

        For some inputs (rate, suction pressure, and discharge pressure), the point may fall outside the capacity
        of one or more compressor stages. In such cases, a `failure_status` describing the issue will be included
        in the `CompressorTrainResult`.

        In certain scenarios, a feasible solution may not exist. For example, the target discharge pressure may
        be too high or too low given the rate and suction pressure. In these cases, calculations are still performed,
        and a result is returned with a `failure_status` indicating whether the target discharge pressure is too high
        or too low. The returned result will include either:
            - No ASV recirculation (if the target pressure is too high, returning results with the maximum possible
              discharge pressure).
            - Maximum recirculation (if the target pressure is too low, returning results with the lowest possible
              discharge pressure).

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        if self.maximum_discharge_pressure is not None:
            if (
                constraints.discharge_pressure is not None
                and constraints.discharge_pressure > self.maximum_discharge_pressure
            ):
                raise ValueError(
                    f"Discharge pressure in input data ({constraints.discharge_pressure}) is "
                    f"larger than maximum allowed discharge pressure in single speed compressor model"
                    f" ({self.maximum_discharge_pressure})"
                )
        if constraints.rate > 0:  # type: ignore[operator]
            if constraints.speed is None and not isinstance(self.data_transfer_object, SingleSpeedCompressorTrainDTO):
                speed = self.find_shaft_speed_given_constraints(
                    constraints=constraints,
                )
                train_result = self.calculate_compressor_train(
                    constraints=constraints.create_conditions_with_new_input(
                        new_speed=speed,
                    ),
                )
            else:
                speed = constraints.speed
                train_result = self.calculate_compressor_train(
                    constraints=constraints,
                )
            if train_result.target_pressure_status == TargetPressureStatus.TARGET_PRESSURES_MET:
                # Solution found
                return train_result
            elif train_result.target_pressure_status is TargetPressureStatus.BELOW_TARGET_DISCHARGE_PRESSURE:
                # Not able to reach the requested discharge pressure at the given speed
                # Return result (with failure) at given speed
                return train_result
            elif self.pressure_control is None:
                return train_result
            else:
                train_result = self.evaluate_with_pressure_control_given_constraints(
                    constraints=constraints.create_conditions_with_new_input(
                        new_speed=speed,
                    )
                )
            return train_result
        else:
            return CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))
