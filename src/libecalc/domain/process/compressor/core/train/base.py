from abc import ABC, abstractmethod
from typing import Generic, TypeVar, cast

import numpy as np
from numpy.typing import NDArray

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.process.compressor.core.base import CompressorModel
from libecalc.domain.process.compressor.core.results import CompressorTrainResultSingleTimeStep
from libecalc.domain.process.compressor.core.train.fluid import FluidStream
from libecalc.domain.process.compressor.core.train.utils.common import PRESSURE_CALCULATION_TOLERANCE
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
            else None
        )
        self.stages = [map_compressor_train_stage_to_domain(stage_dto) for stage_dto in data_transfer_object.stages]
        self.maximum_power = data_transfer_object.maximum_power

        # Will be filled at runtime
        self._target_discharge_pressure = None
        self._target_suction_pressure = None
        self._target_intermediate_pressure = None

    @property
    def number_of_compressor_stages(self) -> int:
        return len(self.stages)

    @property
    def target_discharge_pressure(self):
        return self._target_discharge_pressure

    @target_discharge_pressure.setter
    def target_discharge_pressure(self, value):
        self._target_discharge_pressure = value

    @property
    def target_suction_pressure(self):
        return self._target_suction_pressure

    @target_suction_pressure.setter
    def target_suction_pressure(self, value):
        self._target_suction_pressure = value

    @property
    def target_intermediate_pressure(self):
        return self._target_intermediate_pressure

    @target_intermediate_pressure.setter
    def target_intermediate_pressure(self, value):
        self._target_intermediate_pressure = value

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
        if intermediate_pressure is not None:
            logger.debug(
                f"Evaluating {type(self).__name__} given suction pressure, discharge pressure, "
                "and an inter-stage pressure."
            )
            rate, suction_pressure, discharge_pressure, intermediate_pressure, input_failure_status = (
                validate_model_input(
                    rate=rate,
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                    intermediate_pressure=intermediate_pressure,
                )
            )
            train_results = []
            for rate_value, suction_pressure_value, intermediate_pressure_value, discharge_pressure_value in zip(
                np.transpose(rate),
                suction_pressure,
                intermediate_pressure if intermediate_pressure is not None else [],
                discharge_pressure,
            ):
                if isinstance(rate_value, np.ndarray):
                    rate_value = list(rate_value)
                train_results.append(
                    self._evaluate_rate_ps_pint_pd(
                        rate=rate_value,
                        suction_pressure=suction_pressure_value,
                        discharge_pressure=discharge_pressure_value,
                        intermediate_pressure=intermediate_pressure_value,
                    )
                )

        else:
            logger.debug(f"Evaluating {type(self).__name__} given rate, suction and discharge pressure.")
            rate, suction_pressure, discharge_pressure, _, input_failure_status = validate_model_input(
                rate=rate,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )
            train_results = []
            for rate_value, suction_pressure_value, discharge_pressure_value in zip(
                np.transpose(rate), suction_pressure, discharge_pressure
            ):
                if isinstance(rate_value, np.ndarray):
                    rate_value = list(rate_value)  #  convert to list of rates for each stream
                train_results.append(
                    self._evaluate_rate_ps_pd(
                        rate=rate_value,
                        suction_pressure=suction_pressure_value,
                        discharge_pressure=discharge_pressure_value,
                    )
                )

        power_mw = np.array([result.power_megawatt for result in train_results])
        power_mw_adjusted = np.where(
            power_mw > 0,
            power_mw * self.data_transfer_object.energy_usage_adjustment_factor
            + self.data_transfer_object.energy_usage_adjustment_constant,
            power_mw,
        )

        max_standard_rate = np.full_like(rate, fill_value=INVALID_MAX_RATE, dtype=float)
        if self.data_transfer_object.calculate_max_rate:
            # calculate max standard rate for time steps with valid input
            valid_indices = [
                i
                for (i, failure_status) in enumerate(input_failure_status)
                if failure_status == ModelInputFailureStatus.NO_FAILURE
            ]
            if isinstance(self.data_transfer_object, VariableSpeedCompressorTrainMultipleStreamsAndPressures):
                max_standard_rate_for_valid_indices = self.get_max_standard_rate_per_stream(
                    suction_pressures=suction_pressure[valid_indices],
                    discharge_pressures=discharge_pressure[valid_indices],
                    rates_per_stream=rate[:, valid_indices],
                )
                max_standard_rate[:, valid_indices] = max_standard_rate_for_valid_indices
            else:
                for suction_pressure_value, discharge_pressure_value in zip(
                    suction_pressure[valid_indices], discharge_pressure[valid_indices]
                ):
                    max_standard_rate_for_valid_indices = self.get_max_standard_rate(
                        suction_pressure=suction_pressure_value,
                        discharge_pressure=discharge_pressure_value,
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
    def _evaluate_rate_ps_pd(
        self,
        rate: float | list[float],
        suction_pressure: float,
        discharge_pressure: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """:param rate: Rate in [Sm3/day]
        :param suction_pressure: Suction pressure in [bara]
        :param discharge_pressure: Discharge pressure in [bara]
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
        calculated_suction_pressure: float,
        calculated_discharge_pressure: float,
        calculated_intermediate_pressure: float | None = None,
    ) -> TargetPressureStatus:
        """Check to see how the calculated pressures compare to the required pressures
        Args:
            calculated_suction_pressure: The calculated suction pressure
            calculated_discharge_pressure: The calculated discharge pressure
            calculated_intermediate_pressure: The calculated intermediate pressure
        Returns:
            TargetPressureStatus
        """
        if self.target_suction_pressure:
            if (calculated_suction_pressure / self.target_suction_pressure) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.ABOVE_TARGET_SUCTION_PRESSURE
            if (self.target_suction_pressure / calculated_suction_pressure) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.BELOW_TARGET_SUCTION_PRESSURE
        if self.target_discharge_pressure:
            if (calculated_discharge_pressure / self.target_discharge_pressure) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.ABOVE_TARGET_DISCHARGE_PRESSURE
            if (self.target_discharge_pressure / calculated_discharge_pressure) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.BELOW_TARGET_DISCHARGE_PRESSURE
        if self.target_intermediate_pressure:
            if (
                calculated_intermediate_pressure / self.target_intermediate_pressure
            ) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.ABOVE_TARGET_INTERMEDIATE_PRESSURE
            if (
                self.target_intermediate_pressure / calculated_intermediate_pressure
            ) - 1 > PRESSURE_CALCULATION_TOLERANCE:
                return TargetPressureStatus.BELOW_TARGET_INTERMEDIATE_PRESSURE

        return TargetPressureStatus.TARGET_PRESSURES_MET
