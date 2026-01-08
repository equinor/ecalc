from abc import ABC, abstractmethod
from typing import cast

import numpy as np
from numpy.typing import NDArray

from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.compressor.core.results import (
    CompressorTrainResultSingleTimeStep,
    CompressorTrainStageResultSingleTimeStep,
)
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.compressor.core.train.utils.common import EPSILON, PRESSURE_CALCULATION_TOLERANCE
from libecalc.domain.process.core.results import CompressorTrainResult
from libecalc.domain.process.core.results.compressor import TargetPressureStatus
from libecalc.domain.process.value_objects.fluid_stream import FluidStream
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface

INVALID_MAX_RATE = np.nan


def calculate_pressure_ratio_per_stage(suction_pressure: float, discharge_pressure: float, n_stages: int):
    if n_stages < 1:
        raise ValueError("Can't compute pressure rations when no compressor stages are defined.")
    pressure_ratios = discharge_pressure / suction_pressure
    return pressure_ratios ** (1.0 / n_stages)


class CompressorTrainModel(ABC):
    """Base model for compressor trains."""

    def __init__(
        self,
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
        return max([stage.compressor.compressor_chart.minimum_speed for stage in self.stages])

    @property
    def maximum_speed(self) -> float:
        """Determine the maximum speed of the compressor train if variable speed. Otherwise it doesn't make sense."""
        return min([stage.compressor.compressor_chart.maximum_speed for stage in self.stages])

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
        fluid_factory: FluidFactoryInterface | list[FluidFactoryInterface] | None,
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        intermediate_pressure: NDArray[np.float64] | None = None,
    ):
        if suction_pressure is None:
            raise DomainValidationException("Suction pressure is required for model")
        if discharge_pressure is None:
            raise DomainValidationException("Discharge pressure is required for model")

        self._rate = rate
        self._suction_pressure = suction_pressure
        self._discharge_pressure = discharge_pressure
        self._intermediate_pressure = intermediate_pressure
        self._fluid_factory = fluid_factory

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

        train_results: list[CompressorTrainResultSingleTimeStep] = []
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
            compressor_charts=[stage.compressor.compressor_chart for stage in self.stages],
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
            turbine_result=None,
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

    def train_inlet_stream(
        self,
        pressure: float,
        temperature: float,
        rate: float,
    ) -> FluidStream:
        """Find inlet stream given constraints.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            FluidStream: Inlet fluid stream at the compressor train inlet.
        """
        return self._fluid_factory.create_stream_from_standard_rate(
            pressure_bara=pressure,
            temperature_kelvin=temperature,
            standard_rate_m3_per_day=rate,
        )

    def calculate_pressure_ratios_per_stage(
        self,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> float:
        """Given the number of compressors, and based on the assumption that all compressors have the same pressure ratio,
        compute all pressure ratios.
        """
        return calculate_pressure_ratio_per_stage(
            suction_pressure=suction_pressure, discharge_pressure=discharge_pressure, n_stages=len(self.stages)
        )

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
        fluid_factory: FluidFactoryInterface | None = None,
    ) -> NDArray[np.float64]:
        """
        Calculate the maximum standard volume rate [Sm3/day] that the compressor train can operate at.

        This method determines the maximum rate by evaluating the compressor train's capacity
        based on the given suction and discharge pressures. It considers the compressor's
        operational constraints, including the maximum allowable power and the compressor chart limits.

        Args:
            suction_pressures (float): The suction pressures in bara for each time step.
            discharge_pressures (float): The discharge pressures in bara for each time step.
            fluid_factory (FluidFactoryInterface): The fluid factory interface.

        Returns:
            NDArray[np.float64]: An array of maximum standard rates for each time step.
            If the maximum rate cannot be determined, it returns INVALID_MAX_RATE for that time step.
        """
        if fluid_factory is not None:
            self._fluid_factory = fluid_factory

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
                max_standard_rate[i] = self._get_max_std_rate_single_timestep(constraints=constraints)
            except EcalcError as e:
                logger.exception(e)
                max_standard_rate[i] = float("nan")

        return max_standard_rate

    def get_requested_inlet_pressure(self) -> NDArray[np.float64]:
        return self._suction_pressure

    def get_requested_outlet_pressure(self) -> NDArray[np.float64]:
        return self._discharge_pressure
