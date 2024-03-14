from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar, Union, cast

import numpy as np
from numpy.typing import NDArray

from libecalc import dto
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.core.models import (
    INVALID_INPUT,
    ModelInputFailureStatus,
    validate_model_input,
)
from libecalc.core.models.compressor.base import CompressorModel
from libecalc.core.models.compressor.results import (
    CompressorTrainResultSingleTimeStep,
)
from libecalc.core.models.compressor.train.fluid import FluidStream
from libecalc.core.models.compressor.train.utils.common import (
    PRESSURE_CALCULATION_TOLERANCE,
)
from libecalc.core.models.compressor.utils import map_compressor_train_stage_to_domain
from libecalc.core.models.results import CompressorTrainResult
from libecalc.core.models.results.compressor import (
    CompressorTrainCommonShaftFailureStatus,
)
from libecalc.domain.stream_conditions import StreamConditions
from libecalc.dto.models.compressor.train import CompressorTrain as CompressorTrainDTO
from libecalc.dto.models.compressor.train import (
    SingleSpeedCompressorTrain as SingleSpeedCompressorTrainDTO,
)
from libecalc.dto.types import ChartAreaFlag

TModel = TypeVar("TModel", bound=CompressorTrainDTO)
INVALID_MAX_RATE = INVALID_INPUT


class CompressorTrainModel(CompressorModel, ABC, Generic[TModel]):
    """Base model for compressor trains with common shaft."""

    def __init__(self, data_transfer_object: TModel):
        self.data_transfer_object = data_transfer_object
        self.fluid: Optional[FluidStream] = (
            FluidStream(self.data_transfer_object.fluid_model)
            if self.data_transfer_object.fluid_model is not None
            else None
        )
        self.stages = [map_compressor_train_stage_to_domain(stage_dto) for stage_dto in data_transfer_object.stages]

    @property
    def minimum_speed(self) -> float:
        """Determine the minimum speed of the compressor train if variable speed. Otherwise, it doesn't make sense."""
        return max([stage.compressor_chart.minimum_speed for stage in self.stages])

    @property
    def maximum_speed(self) -> float:
        """Determine the maximum speed of the compressor train if variable speed. Otherwise it doesn't make sense."""
        return min([stage.compressor_chart.maximum_speed for stage in self.stages])

    @property
    def pressure_control(self) -> Optional[dto.types.FixedSpeedPressureControl]:
        return self.data_transfer_object.pressure_control

    @property
    def maximum_discharge_pressure(self) -> Optional[float]:
        if isinstance(self.data_transfer_object, SingleSpeedCompressorTrainDTO):
            return self.data_transfer_object.maximum_discharge_pressure
        else:
            return None

    def evaluate_rate_ps_pd(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> CompressorTrainResult:
        """Evaluate compressor train total power given rate, suction pressure and discharge pressure.

        Pre-processing:
            Set total power for zero (or negative) rates to 0.0
            Set total power for zero pressure increase to 0.0
            Calculate power for valid points (positive pressures, discharge pressure larger than suction pressure)

        Note:
            Rate when containing multiple streams can be indexed rate[stream, time_step].
            If two stream and 3 timesteps, then the array will be created like: np.array([[t1, t2, t3], [t1, t2, t3]]).

            When pre-processing the data we need to compare rates per timestep by using e.g. np.min(rate, axis=0)

        :param rate:
            Rate in [Sm3/day] per timestep and per stream.
            Will be only 1 stream for all models except the multiple streams model.
        :param suction_pressure: Suction pressure in [bara]
        :param discharge_pressure: Discharge pressure in [bara]
        """
        logger.debug(f"Evaluating {type(self).__name__} given rate, suction and discharge pressure.")

        rate, suction_pressure, discharge_pressure, _, input_failure_status = validate_model_input(
            rate=rate,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )
        train_results = self._evaluate_rate_ps_pd(
            rate=rate,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )

        power_mw = np.array([result.power_megawatt for result in train_results])
        power_mw_adjusted = np.where(
            power_mw > 0, power_mw + self.data_transfer_object.energy_usage_adjustment_constant, power_mw
        )

        max_standard_rate = np.full_like(rate, fill_value=INVALID_MAX_RATE, dtype=float)
        if self.data_transfer_object.calculate_max_rate:
            # calculate max standard rate for time steps with valid input
            valid_indices = [
                i
                for (i, failure_status) in enumerate(input_failure_status)
                if failure_status == ModelInputFailureStatus.NO_FAILURE
            ]
            if isinstance(self.data_transfer_object, dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures):
                max_standard_rate_for_valid_indices = self.get_max_standard_rate_per_stream(
                    suction_pressures=suction_pressure[valid_indices],
                    discharge_pressures=discharge_pressure[valid_indices],
                    rates_per_stream=rate[:, valid_indices],
                )
                max_standard_rate[:, valid_indices] = max_standard_rate_for_valid_indices
            else:
                max_standard_rate_for_valid_indices = self.get_max_standard_rate(
                    suction_pressures=suction_pressure[valid_indices],
                    discharge_pressures=discharge_pressure[valid_indices],
                )
                max_standard_rate[valid_indices] = max_standard_rate_for_valid_indices

        stage_results = CompressorTrainResultSingleTimeStep.from_result_list_to_dto(
            result_list=train_results,
            compressor_charts=[stage.compressor_chart.data_transfer_object for stage in self.stages],
        )

        failure_status = self.evaluate_train_results_for_failure_status(
            train_results=train_results,
            power=power_mw_adjusted,
            target_suction_pressures=suction_pressure,
            target_discharge_pressures=discharge_pressure,
        )

        for i, model_failure in enumerate(input_failure_status):
            if model_failure is not ModelInputFailureStatus.NO_FAILURE:
                failure_status[i] = model_failure

        return CompressorTrainResult(
            energy_usage=list(power_mw_adjusted),
            energy_usage_unit=Unit.MEGA_WATT,
            power=list(power_mw_adjusted),
            power_unit=Unit.MEGA_WATT,
            rate_sm3_day=cast(list, rate.tolist()),
            max_standard_rate=cast(list, max_standard_rate.tolist()),
            stage_results=stage_results,
            failure_status=failure_status,
        )

    def evaluate_streams(
        self,
        inlet_streams: List[StreamConditions],
        outlet_stream: StreamConditions,
    ) -> CompressorTrainResult:
        """
        Evaluate model based on inlet streams and the expected outlet stream.
        Args:
            inlet_streams:
            outlet_stream:

        Returns:

        """
        mixed_inlet_stream = StreamConditions.mix_all(inlet_streams)
        return self.evaluate_rate_ps_pd(
            rate=np.asarray([mixed_inlet_stream.rate.value]),
            suction_pressure=np.asarray([mixed_inlet_stream.pressure.value]),
            discharge_pressure=np.asarray([outlet_stream.pressure.value]),
        )

    def evaluate_train_results_for_failure_status(
        self,
        train_results: List[CompressorTrainResultSingleTimeStep],
        power: NDArray[np.float64],
        target_suction_pressures: NDArray[np.float64],
        target_discharge_pressures: NDArray[np.float64],
        target_intermediate_pressures: Optional[NDArray[np.float64]] = None,
    ) -> List[CompressorTrainCommonShaftFailureStatus]:
        """Takes the separate stage results and compares to the given pressure and power constraints

        Args:
            stage_results:
            target_suction_pressure:
            target_discharge_pressure:
            target_intermediate_pressure:

        Returns:

        """
        failure_status = [None] * len(train_results)
        for i, train_result in enumerate(train_results):
            target_suction_pressure = target_suction_pressures[i]
            target_intermediate_pressure = (
                target_intermediate_pressures[i] if target_intermediate_pressures is not None else None
            )
            target_discharge_pressure = target_discharge_pressures[i]

            if not all(r.is_valid for r in train_result.stage_results):
                for stage in train_result.stage_results:
                    if not stage.is_valid:
                        if stage.chart_area_flag in (
                            ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE,
                            ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_ABOVE_MAXIMUM_FLOW_RATE,
                        ):
                            failure_status[i] = CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE
                            break
                        elif stage.chart_area_flag in (
                            ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
                            ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_BELOW_MINIMUM_FLOW_RATE,
                        ):
                            failure_status[i] = CompressorTrainCommonShaftFailureStatus.BELOW_MINIMUM_FLOW_RATE
                            break

            elif train_result.discharge_pressure * (1 + PRESSURE_CALCULATION_TOLERANCE) < target_discharge_pressure:
                failure_status[i] = CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH
            elif train_result.suction_pressure * (1 - PRESSURE_CALCULATION_TOLERANCE) > target_suction_pressure:
                failure_status[i] = CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH
            elif train_result.discharge_pressure * (1 - PRESSURE_CALCULATION_TOLERANCE) > target_discharge_pressure:
                failure_status[i] = CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW
            elif target_intermediate_pressure is not None:
                intermediate_pressure_to_check = train_result.stage_results[
                    self.data_transfer_object.stage_number_interstage_pressure - 1
                ].discharge_pressure
                if intermediate_pressure_to_check * (1 - PRESSURE_CALCULATION_TOLERANCE) > target_intermediate_pressure:
                    failure_status[i] = CompressorTrainCommonShaftFailureStatus.TARGET_INTERMEDIATE_PRESSURE_TOO_LOW
                elif (
                    intermediate_pressure_to_check * (1 + PRESSURE_CALCULATION_TOLERANCE) < target_intermediate_pressure
                ):
                    failure_status[i] = CompressorTrainCommonShaftFailureStatus.TARGET_INTERMEDIATE_PRESSURE_TOO_HIGH
            elif self.data_transfer_object.maximum_power:
                if self.data_transfer_object.maximum_power < power[i]:
                    failure_status[i] = CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_POWER

        return failure_status

    @abstractmethod
    def _evaluate_rate_ps_pd(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> List[CompressorTrainResultSingleTimeStep]:
        """:param rate: Rate in [Sm3/day]
        :param suction_pressure: Suction pressure in [bara]
        :param discharge_pressure: Discharge pressure in [bara]
        """
        ...

    def calculate_pressure_ratios_per_stage(
        self,
        suction_pressure: Union[NDArray[np.float64], float],
        discharge_pressure: Union[NDArray[np.float64], float],
    ) -> Union[NDArray[np.float64], float]:
        """Given the number of compressors, and based on the assumption that all compressors have the same pressure ratio,
        compute all pressure ratios.
        """
        if len(self.stages) < 1:
            raise ValueError("Can't compute pressure rations when no compressor stages are defined.")
        pressure_ratios = np.divide(
            discharge_pressure, suction_pressure, out=np.ones_like(suction_pressure), where=suction_pressure != 0
        )
        return pressure_ratios ** (1.0 / len(self.stages))
