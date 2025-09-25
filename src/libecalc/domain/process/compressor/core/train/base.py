from abc import ABC, abstractmethod
from typing import cast

import numpy as np
from numpy.typing import NDArray

from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.process.compressor.core.base import CompressorModel
from libecalc.domain.process.compressor.core.results import (
    CompressorTrainResultSingleTimeStep,
    CompressorTrainStageResultSingleTimeStep,
)
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.compressor.core.train.utils.common import EPSILON, PRESSURE_CALCULATION_TOLERANCE
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import (
    find_root,
    maximize_x_given_boolean_condition_function,
)
from libecalc.domain.process.core.results import CompressorTrainResult
from libecalc.domain.process.core.results.compressor import TargetPressureStatus
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface

INVALID_MAX_RATE = np.nan


class CompressorTrainModel(CompressorModel, ABC):
    """Base model for compressor trains with common shaft."""

    def __init__(
        self,
        fluid_factory: FluidFactoryInterface,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        stages: list[CompressorTrainStage],
        maximum_power: float | None = None,
        pressure_control: FixedSpeedPressureControl | None = None,
        maximum_discharge_pressure: float | None = None,
        calculate_max_rate: bool | None = False,
        stage_number_interstage_pressure: int | None = None,
    ):
        # self.data_transfer_object = data_transfer_object
        self.energy_usage_adjustment_constant = energy_usage_adjustment_constant
        self.energy_usage_adjustment_factor = energy_usage_adjustment_factor
        self.fluid_factory = fluid_factory
        self.stages = stages
        self.maximum_power = maximum_power
        self._maximum_discharge_pressure = maximum_discharge_pressure
        self._pressure_control = pressure_control
        self.calculate_max_rate = calculate_max_rate
        self.stage_number_interstage_pressure = stage_number_interstage_pressure

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
        return self._pressure_control

    @pressure_control.setter
    def pressure_control(self, value: FixedSpeedPressureControl | None):
        self._pressure_control = value

    @property
    def maximum_discharge_pressure(self) -> float | None:
        return self._maximum_discharge_pressure

    def get_consumption_type(self) -> ConsumptionType:
        # Electricity here represents POWER, not electricity specifically. CompressorTrainModel consumes POWER, but not
        # necessarily electricity. The alternative is FUEL. CompressorWithTurbine is used to create a compressor train
        # that consumes FUEL, the turbine is modeled separately.
        return ConsumptionType.ELECTRICITY

    def set_evaluation_input(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64] | None,
        discharge_pressure: NDArray[np.float64] | None,
        intermediate_pressure: NDArray[np.float64] | None = None,
    ):
        if suction_pressure is None:
            raise ValueError("Suction pressure is required for model")
        if discharge_pressure is None:
            raise ValueError("Discharge pressure is required for model")

        self._rate = rate
        self._suction_pressure = suction_pressure
        self._discharge_pressure = discharge_pressure
        self._intermediate_pressure = intermediate_pressure

    def evaluate(
        self,
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

        train_results = []
        for rate_value, suction_pressure_value, intermediate_pressure_value, discharge_pressure_value in zip(
            np.transpose(self._rate),
            self._suction_pressure,
            self._intermediate_pressure
            if self._intermediate_pressure is not None
            else [None] * len(self._suction_pressure),
            self._discharge_pressure,
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
            power_mw * self.energy_usage_adjustment_factor + self.energy_usage_adjustment_constant,
            power_mw,
        )

        max_standard_rate = np.full_like(self._suction_pressure, fill_value=INVALID_MAX_RATE, dtype=float)
        if self.calculate_max_rate:
            max_standard_rate = self.get_max_standard_rate(
                suction_pressures=self._suction_pressure,
                discharge_pressures=self._discharge_pressure,
            )

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
            rate_sm3_day=cast(list, self._rate.tolist()),
            max_standard_rate=cast(list, max_standard_rate.tolist()),
            stage_results=stage_results,
            failure_status=[t.failure_status for t in train_results],
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
                    results.stage_results[self.stage_number_interstage_pressure - 1].discharge_pressure
                    if self.stage_number_interstage_pressure is not None
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

    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
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
