import numpy as np

from libecalc.common.time_utils import Periods
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft_multiple_streams_and_pressures import (
    CompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_fluid_density import TimeSeriesFluidDensity
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor
from libecalc.domain.time_series_pressure import TimeSeriesPressure


class CompressorEvaluationInput:
    """
    Encapsulates all input data required to configure and apply evaluation parameters to a compressor model.

    Args:
        rate (TimeSeriesFlowRate | list[TimeSeriesFlowRate]): the flow rate expression(s).
        fluid_factory (FluidFactoryInterface | list[FluidFactoryInterface] | None): the fluid factory instance describing compositional properties for the process fluid.
        power_loss_factor (TimeSeriesPowerLossFactor | None): expression for power loss factor.
        suction_pressure (TimeSeriesPressure | None): expression for the inlet (suction) pressure.
        discharge_pressure (TimeSeriesPressure | None): expression for the outlet (discharge) pressure.
        intermediate_pressure (TimeSeriesPressure | None): expression for intermediate pressure.
    """

    def __init__(
        self,
        rate: TimeSeriesFlowRate | list[TimeSeriesFlowRate],
        fluid_factory: FluidFactoryInterface | list[FluidFactoryInterface],
        suction_pressure: TimeSeriesPressure,
        discharge_pressure: TimeSeriesPressure,
        power_loss_factor: TimeSeriesPowerLossFactor | None = None,
        intermediate_pressure: TimeSeriesPressure | None = None,
    ):
        self._rate = rate
        self._fluid_factory = fluid_factory
        self._power_loss_factor = power_loss_factor
        self._suction_pressure = suction_pressure
        self._discharge_pressure = discharge_pressure
        self._intermediate_pressure = intermediate_pressure

    @property
    def power_loss_factor(self) -> TimeSeriesPowerLossFactor | None:
        return self._power_loss_factor

    @property
    def periods(self) -> Periods:
        if isinstance(self._rate, list):
            return self._rate[0].get_periods()
        return self._rate.get_periods()

    def apply_to_model(self, compressor_model: CompressorTrainModel | CompressorWithTurbineModel):
        rate_expr = self._rate if isinstance(self._rate, list) else [self._rate]

        model_to_check = (
            compressor_model.compressor_model
            if isinstance(compressor_model, CompressorWithTurbineModel)
            else compressor_model
        )

        if not isinstance(model_to_check, CompressorTrainCommonShaftMultipleStreamsAndPressures):
            assert len(rate_expr) == 1
            stream_day_rate = np.asarray(rate_expr[0].get_stream_day_values(), dtype=np.float64)
        else:
            stream_day_rate = np.array([rate.get_stream_day_values() for rate in rate_expr], dtype=np.float64)

        intermediate_pressure = (
            np.asarray(self._intermediate_pressure.get_values(), dtype=np.float64)
            if self._intermediate_pressure is not None
            else None
        )
        suction_pressure = np.asarray(self._suction_pressure.get_values(), dtype=np.float64)
        discharge_pressure = np.asarray(self._discharge_pressure.get_values(), dtype=np.float64)

        compressor_model.set_evaluation_input(
            rate=stream_day_rate,
            fluid_factory=self._fluid_factory,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            intermediate_pressure=intermediate_pressure,
        )


class CompressorSampledEvaluationInput:
    """
    Encapsulates all input data required to configure and apply evaluation parameters to a sampled compressor model.

    Args:
        rate (TimeSeriesFlowRate | list[TimeSeriesFlowRate]): the flow rate expression(s).
        power_loss_factor (TimeSeriesPowerLossFactor | None): expression for power loss factor.
        suction_pressure (TimeSeriesPressure | None): expression for the inlet (suction) pressure.
        discharge_pressure (TimeSeriesPressure | None): expression for the outlet (discharge) pressure.
    """

    def __init__(
        self,
        rate: TimeSeriesFlowRate | list[TimeSeriesFlowRate],
        power_loss_factor: TimeSeriesPowerLossFactor | None = None,
        suction_pressure: TimeSeriesPressure | None = None,
        discharge_pressure: TimeSeriesPressure | None = None,
    ):
        self._rate = rate
        self._power_loss_factor = power_loss_factor
        self._suction_pressure = suction_pressure
        self._discharge_pressure = discharge_pressure

    @property
    def power_loss_factor(self) -> TimeSeriesPowerLossFactor | None:
        return self._power_loss_factor

    @property
    def periods(self) -> Periods:
        if isinstance(self._rate, list):
            return self._rate[0].get_periods()
        return self._rate.get_periods()

    def apply_to_model(self, compressor_model: CompressorModelSampled | CompressorWithTurbineModel):
        rate_expr = [self._rate]

        assert len(rate_expr) == 1
        stream_day_rate = np.asarray(rate_expr[0].get_stream_day_values(), dtype=np.float64)

        suction_pressure = (
            np.asarray(self._suction_pressure.get_values(), dtype=np.float64)
            if self._suction_pressure is not None
            else None
        )
        discharge_pressure = (
            np.asarray(self._discharge_pressure.get_values(), dtype=np.float64)
            if self._discharge_pressure is not None
            else None
        )

        compressor_model.set_evaluation_input(
            rate=stream_day_rate,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )


class PumpEvaluationInput:
    def __init__(
        self,
        rate: TimeSeriesFlowRate,
        suction_pressure: TimeSeriesPressure,
        discharge_pressure: TimeSeriesPressure,
        fluid_density: TimeSeriesFluidDensity,
        power_loss_factor: TimeSeriesPowerLossFactor | None = None,
    ):
        self._rate = rate
        self._fluid_density = fluid_density
        self._suction_pressure = suction_pressure
        self._discharge_pressure = discharge_pressure
        self._power_loss_factor = power_loss_factor

    @property
    def power_loss_factor(self) -> TimeSeriesPowerLossFactor | None:
        return self._power_loss_factor

    @property
    def periods(self) -> Periods:
        if isinstance(self._rate, list):
            return self._rate[0].get_periods()
        return self._rate.get_periods()

    def apply_to_model(self, pump_model: PumpModel):
        stream_day_rate = np.asarray(self._rate.get_stream_day_values(), dtype=np.float64)

        pump_model.set_evaluation_input(
            stream_day_rate=stream_day_rate,
            suction_pressure=np.asarray(self._suction_pressure.get_values(), dtype=np.float64),
            discharge_pressure=np.asarray(self._discharge_pressure.get_values(), dtype=np.float64),
            fluid_density=np.asarray(self._fluid_density.get_values(), dtype=np.float64),
        )
