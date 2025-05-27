from abc import ABC, abstractmethod
from typing import Generic, TypeVar, cast

import numpy as np
from numpy.typing import NDArray

from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.fluid import FluidStream as FluidStreamDTO
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.process.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.compressor.core.base import CompressorModel
from libecalc.domain.process.compressor.core.results import (
    CompressorTrainResultSingleTimeStep,
    CompressorTrainStageResultSingleTimeStep,
)
from libecalc.domain.process.compressor.core.train.fluid import FluidStream
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.compressor.core.train.utils.common import EPSILON, PRESSURE_CALCULATION_TOLERANCE
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import (
    find_root,
    maximize_x_given_boolean_condition_function,
)
from libecalc.domain.process.compressor.core.utils import map_compressor_train_stage_to_domain
from libecalc.domain.process.compressor.dto.train import CompressorTrain as CompressorTrainDTO
from libecalc.domain.process.compressor.dto.train import (
    SingleSpeedCompressorTrain as SingleSpeedCompressorTrainDTO,
)
from libecalc.domain.process.compressor.dto.train import VariableSpeedCompressorTrainMultipleStreamsAndPressures
from libecalc.domain.process.core import (
    INVALID_INPUT,
    ModelInputFailureStatus,
    validate_model_input,
)
from libecalc.domain.process.core.results import CompressorTrainResult
from libecalc.domain.process.core.results.compressor import TargetPressureStatus

TModel = TypeVar("TModel", bound=CompressorTrainDTO)
INVALID_MAX_RATE = INVALID_INPUT


class CompressorTrainModel(CompressorModel, ABC, Generic[TModel]):
    """Base model for compressor trains with common shaft."""

    def __init__(self, data_transfer_object: TModel):
        self.data_transfer_object = data_transfer_object
        self.fluid: FluidStream | None = (
            FluidStream(self.data_transfer_object.fluid_model)
            if self.data_transfer_object.fluid_model is not None
            else FluidStream(self.data_transfer_object.streams[0].fluid_model)
        )
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
            max_standard_rate_for_valid_indices = []
            if isinstance(self.data_transfer_object, VariableSpeedCompressorTrainMultipleStreamsAndPressures):
                for rate_value, suction_pressure_value, discharge_pressure_value in zip(
                    np.transpose(rate[:, valid_indices]),
                    suction_pressure[valid_indices],
                    discharge_pressure[valid_indices],
                ):
                    max_standard_rate_for_valid_indices.append(
                        self.get_max_standard_rate(
                            constraints=CompressorTrainEvaluationInput(
                                suction_pressures=suction_pressure_value,
                                discharge_pressure=discharge_pressure_value,
                                rate=rate_value[0],
                                rates_per_stresm=rate_value,
                            )
                        )
                    )
                max_standard_rate[valid_indices] = max_standard_rate_for_valid_indices
            else:
                for suction_pressure_value, discharge_pressure_value in zip(
                    suction_pressure[valid_indices], discharge_pressure[valid_indices]
                ):
                    max_standard_rate_for_valid_indices.append(
                        self.get_max_standard_rate(
                            constraints=CompressorTrainEvaluationInput(
                                suction_pressure=suction_pressure_value,
                                discharge_pressure=discharge_pressure_value,
                            )
                        )
                    )
                max_standard_rate[valid_indices] = max_standard_rate_for_valid_indices

        (
            inlet_stream_condition,
            outlet_stream_condition,
            stage_results,
        ) = CompressorTrainResultSingleTimeStep.from_result_list_to_dto(
            result_list=train_results,
            compressor_charts=[stage.compressor_chart.data_transfer_object for stage in self.stages],
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
                input_failure_status[i]
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
            calculated_suction_pressure = results[0].inlet_pressure
            calculated_discharge_pressure = results[-1].discharge_pressure
            calculated_intermediate_pressure = None
        else:
            calculated_suction_pressure = results.suction_pressure
            calculated_discharge_pressure = results.discharge_pressure
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
        if constraints.suction_pressure:
            if (calculated_suction_pressure / constraints.suction_pressure) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.ABOVE_TARGET_SUCTION_PRESSURE
            if (constraints.suction_pressure / calculated_suction_pressure) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.BELOW_TARGET_SUCTION_PRESSURE
        if constraints.discharge_pressure:
            if (calculated_discharge_pressure / constraints.discharge_pressure) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.ABOVE_TARGET_DISCHARGE_PRESSURE
            if (constraints.discharge_pressure / calculated_discharge_pressure) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.BELOW_TARGET_DISCHARGE_PRESSURE
        if constraints.interstage_pressure:
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
            new_outlet_stream = FluidStream(
                fluid_model=train_result.outlet_stream,
                pressure_bara=constraints.discharge_pressure,
                temperature_kelvin=train_result.outlet_stream.temperature_kelvin,
            )
            train_result.outlet_stream = FluidStreamDTO.from_fluid_domain_object(fluid_stream=new_outlet_stream)
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

        def _calculate_train_result_given_inlet_pressure(
            inlet_pressure: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Note that we use outside variables for clarity and to avoid class instances."""
            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_suction_pressure=inlet_pressure,
                ),
            )

        result_inlet_pressure = find_root(
            lower_bound=EPSILON + self.stages[0].pressure_drop_ahead_of_stage,
            upper_bound=constraints.discharge_pressure,
            func=lambda x: _calculate_train_result_given_inlet_pressure(inlet_pressure=x).discharge_pressure
            - constraints.discharge_pressure,
        )

        train_result = _calculate_train_result_given_inlet_pressure(inlet_pressure=result_inlet_pressure)
        if result_inlet_pressure < constraints.suction_pressure:
            # Now the train inlet pressure has been reduced to the point where the discharge pressure is met, mimicking
            # a choke valve between the inlet of the train and the inlet of the first stage.
            new_inlet_stream = FluidStream(
                fluid_model=train_result.inlet_stream,
                pressure_bara=constraints.suction_pressure,
                temperature_kelvin=train_result.inlet_stream.temperature_kelvin,
            )
            train_result.inlet_stream = FluidStreamDTO.from_fluid_domain_object(fluid_stream=new_inlet_stream)

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
            constraints.discharge_pressure > train_result_for_minimum_asv_rate_fraction.discharge_pressure
        ):
            return train_result_for_minimum_asv_rate_fraction
        train_result_for_maximum_asv_rate_fraction = _calculate_train_result_given_asv_rate_margin(
            asv_rate_fraction=maximum_asv_fraction
        )
        if constraints.discharge_pressure < train_result_for_maximum_asv_rate_fraction.discharge_pressure:
            return train_result_for_maximum_asv_rate_fraction

        result_asv_rate_margin = find_root(
            lower_bound=0.0,
            upper_bound=1.0,
            func=lambda x: _calculate_train_result_given_asv_rate_margin(asv_rate_fraction=x).discharge_pressure
            - constraints.discharge_pressure,
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
        mass_rate_kg_per_hour = self.fluid.standard_rate_to_mass_rate(standard_rates=constraints.rate)
        inlet_stream_train = self.fluid.get_fluid_stream(
            pressure_bara=constraints.suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )
        pressure_ratio_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=constraints.suction_pressure,
            discharge_pressure=constraints.discharge_pressure,
        )
        inlet_stream_stage = outlet_stream_stage = inlet_stream_train
        stage_results = []
        for stage in self.stages:
            outlet_pressure_for_stage = inlet_stream_stage.pressure_bara * pressure_ratio_per_stage
            stage_result = stage.evaluate_given_speed_and_target_discharge_pressure(
                target_discharge_pressure=outlet_pressure_for_stage,
                mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                inlet_stream_stage=inlet_stream_stage,
            )
            outlet_stream_stage = inlet_stream_stage.set_new_pressure_and_temperature(
                new_pressure_bara=stage_result.outlet_stream.pressure_bara,
                new_temperature_kelvin=stage_result.outlet_stream.temperature_kelvin,
            )
            inlet_stream_stage = outlet_stream_stage
            stage_results.append(stage_result)

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            constraints=constraints,
            results=stage_results,
        )
        return CompressorTrainResultSingleTimeStep(
            inlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=inlet_stream_train),
            outlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=outlet_stream_stage),
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
        minimum_mass_rate_kg_per_hour = self.fluid.standard_rate_to_mass_rate(
            standard_rates=constraints.rate,
        )
        # Iterate on rate until pressures are met
        train_inlet_stream = self.fluid.get_fluid_stream(
            pressure_bara=constraints.suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )

        def _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=mass_rate_kg_per_hour),
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
            self.stages[0].compressor_chart.minimum_rate * train_inlet_stream.density,
        )
        maximum_mass_rate = self.stages[0].compressor_chart.maximum_rate * train_inlet_stream.density

        # if the minimum_mass_rate_kg_per_hour(i.e. before increasing rate with recirculation to lower pressure)
        # is already larger than the maximum mass rate, there is no need for optimization - just add result
        # with minimum_mass_rate_kg_per_hour (which will fail with above maximum flow rate)
        if minimum_mass_rate_kg_per_hour > maximum_mass_rate:
            return _calculate_train_result_given_mass_rate(mass_rate_kg_per_hour=minimum_mass_rate_kg_per_hour)

        train_result_for_minimum_mass_rate = _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour=minimum_mass_rate
        )
        train_result_for_maximum_mass_rate = _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour=maximum_mass_rate
        )
        if train_result_for_minimum_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
            if not train_result_for_maximum_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
                # find the maximum additional_mass_rate that gives train_results.is_valid
                maximum_mass_rate = maximize_x_given_boolean_condition_function(
                    x_min=0.0,  # Searching between near zero and the invalid mass rate above.
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
                x_min=-maximum_mass_rate,  # Searching between near zero and the invalid mass rate above.
                x_max=-minimum_mass_rate,
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
                mass_rate_kg_per_hour=minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)
            )
            while not train_result_for_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
                inc += 0.1
                if inc >= 1:
                    logger.error("Single speed train with Common ASV pressure control has no solution!")
                train_result_for_mass_rate = _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)
                )

            # found one solution, now find min and max
            minimum_mass_rate = -maximize_x_given_boolean_condition_function(
                x_min=-(
                    minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)
                ),  # Searching between near zero and the invalid mass rate above.
                x_max=-minimum_mass_rate,
                bool_func=lambda x: _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=-x
                ).mass_rate_asv_corrected_is_constant_for_stages,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            maximum_mass_rate = maximize_x_given_boolean_condition_function(
                x_min=(
                    minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)
                ),  # Searching between near zero and the invalid mass rate above.
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
        if constraints.discharge_pressure > train_result_for_minimum_mass_rate.discharge_pressure:
            # will never reach target pressure, too high
            return train_result_for_minimum_mass_rate
        if constraints.discharge_pressure < train_result_for_maximum_mass_rate.discharge_pressure:
            # will never reach target pressure, too low
            return train_result_for_maximum_mass_rate

        result_mass_rate = find_root(
            lower_bound=minimum_mass_rate,
            upper_bound=maximum_mass_rate,
            func=lambda x: _calculate_train_result_given_mass_rate(mass_rate_kg_per_hour=x).discharge_pressure
            - constraints.discharge_pressure,
        )
        # This mass rate is the mass rate to use as mass rate after asv for each stage,
        # thus the asv in each stage should be set to correspond to this mass rate
        return _calculate_train_result_given_additional_mass_rate(
            additional_mass_rate_kg_per_hour=result_mass_rate - minimum_mass_rate_kg_per_hour
        )

    def get_max_standard_rate(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> float:
        """
        Calculate the maximum standard volume rate [Sm3/day] that the compressor train can operate at.

        This method determines the maximum rate by evaluating the compressor train's capacity
        based on the given suction and discharge pressures. It considers the compressor's
        operational constraints, including the maximum allowable power and the compressor chart limits.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            float: The maximum standard volume rate in Sm3/day. Returns NaN if the calculation fails.
        """
        try:
            max_std_rate = self._get_max_std_rate_single_timestep(
                constraints=constraints,
            )
        except EcalcError as e:
            logger.exception(e)
            max_std_rate = float("nan")

        return max_std_rate

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
        minimum_speed = lower_bound_for_speed if lower_bound_for_speed else self.minimum_speed
        maximum_speed = upper_bound_for_speed if upper_bound_for_speed else self.maximum_speed
        if constraints.speed is not None:
            return constraints.speed

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
            return self.maximum_speed
        if not train_result_for_minimum_speed.within_capacity:
            # rate is above maximum rate for minimum speed. Find the lowest minimum speed which gives a valid result
            minimum_speed = -maximize_x_given_boolean_condition_function(
                x_min=-self.maximum_speed,
                x_max=-self.minimum_speed,
                bool_func=lambda x: _calculate_compressor_train(_speed=-x).within_capacity,
            )
            train_result_for_minimum_speed = _calculate_compressor_train(_speed=minimum_speed)

        # Solution 1, iterate on speed until target discharge pressure is found
        if (
            train_result_for_minimum_speed.discharge_pressure
            <= constraints.discharge_pressure
            <= train_result_for_maximum_speed.discharge_pressure
        ):
            speed = find_root(
                lower_bound=self.minimum_speed,
                upper_bound=self.maximum_speed,
                func=lambda x: _calculate_compressor_train(_speed=x).discharge_pressure
                - constraints.discharge_pressure,
            )

            return speed

        # Solution 2, target pressure is too low:
        if constraints.discharge_pressure < train_result_for_minimum_speed.discharge_pressure:
            return minimum_speed

        # Solution 3, target discharge pressure is too high
        return self.maximum_speed
