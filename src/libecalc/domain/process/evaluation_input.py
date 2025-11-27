import numpy as np
from numpy.typing import NDArray

from libecalc.common.time_utils import Periods
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.pump.pump_evaluation_input import PumpEvaluationInputSingleTimeStep
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_fluid_density import TimeSeriesFluidDensity
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor
from libecalc.domain.time_series_pressure import TimeSeriesPressure


class CompressorEvaluationInput:
    """
    Encapsulates all input data required to configure and apply evaluation parameters to a compressor model.

    Attributes:
        rate_expression (TimeSeriesFlowRate | list[TimeSeriesFlowRate]): the flow rate expression(s).
        fluid_factory (FluidFactoryInterface | list[FluidFactoryInterface] | None): the fluid factory instance describing compositional properties for the process fluid.
        power_loss_factor (TimeSeriesPowerLossFactor | None): expression for power loss factor.
        suction_pressure_expression (TimeSeriesPressure | None): expression for the inlet (suction) pressure.
        discharge_pressure_expression (TimeSeriesPressure | None): expression for the outlet (discharge) pressure.
        intermediate_pressure_expression (TimeSeriesPressure | None): expression for intermediate pressure.
    """

    def __init__(
        self,
        rate_expression: TimeSeriesFlowRate | list[TimeSeriesFlowRate],
        fluid_factory: FluidFactoryInterface | list[FluidFactoryInterface],
        suction_pressure_expression: TimeSeriesPressure,
        discharge_pressure_expression: TimeSeriesPressure,
        power_loss_factor: TimeSeriesPowerLossFactor | None = None,
        intermediate_pressure_expression: TimeSeriesPressure | None = None,
    ):
        self._rate_expression = rate_expression
        self._fluid_factory = fluid_factory
        self._power_loss_factor = power_loss_factor
        self._suction_pressure_expression = suction_pressure_expression
        self._discharge_pressure_expression = discharge_pressure_expression
        self._intermediate_pressure_expression = intermediate_pressure_expression

    @property
    def power_loss_factor(self) -> TimeSeriesPowerLossFactor | None:
        return self._power_loss_factor

    @property
    def stream_day_rate(self) -> NDArray[np.float64]:
        rate_expr = self._rate_expression if isinstance(self._rate_expression, list) else [self._rate_expression]

        if not isinstance(self._fluid_factory, list):
            assert len(rate_expr) == 1
            return np.asarray(rate_expr[0].get_stream_day_values(), dtype=np.float64)
        else:
            return np.array([rate.get_stream_day_values() for rate in rate_expr], dtype=np.float64)

    @property
    def intermediate_pressure(self) -> NDArray[np.float64] | None:
        return (
            np.asarray(self._intermediate_pressure_expression.get_values(), dtype=np.float64)
            if self._intermediate_pressure_expression is not None
            else None
        )

    @property
    def suction_pressure(self) -> NDArray[np.float64]:
        return np.asarray(self._suction_pressure_expression.get_values(), dtype=np.float64)

    @property
    def discharge_pressure(self) -> NDArray[np.float64]:
        return np.asarray(self._discharge_pressure_expression.get_values(), dtype=np.float64)

    @property
    def periods(self) -> Periods:
        if isinstance(self._rate_expression, list):
            return self._rate_expression[0].get_periods()
        return self._rate_expression.get_periods()

    def get_single_time_step_inputs(self) -> list[CompressorTrainEvaluationInput]:
        rates = self.stream_day_rate

        n_timesteps = rates.shape[-1] if rates.ndim > 1 else rates.shape[0]
        result = []
        for i in range(n_timesteps):
            # If rates is 2D (multiple streams), select all streams at timestep i.
            # If rates is 1D (single stream), select the scalar value at timestep i.
            rate_value = rates[:, i] if rates.ndim > 1 else rates[i]

            # At this point, rate_value is either a scalar (single stream) or a 1D array (multiple streams).
            if isinstance(rate_value, np.ndarray):
                rate_value = list(rate_value)
                constraints_rate = rate_value[0]
                constraints_stream_rates = rate_value
            else:
                constraints_rate = rate_value
                constraints_stream_rates = None
            suction_pressure = self.suction_pressure[i]
            discharge_pressure = self.discharge_pressure[i]
            intermediate_pressure = self.intermediate_pressure[i] if self.intermediate_pressure is not None else None
            fluid_factory = self._fluid_factory
            result.append(
                CompressorTrainEvaluationInput(
                    rate=constraints_rate,
                    fluid_factory=fluid_factory,
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                    interstage_pressure=intermediate_pressure,
                    stream_rates=constraints_stream_rates,
                )
            )
        return result


# class CompressorEvaluationInputOld:
#     """
#     Encapsulates all input data required to configure and apply evaluation parameters to a compressor model.
#
#     Attributes:
#         rate_expression (TimeSeriesFlowRate | list[TimeSeriesFlowRate]): the flow rate expression(s).
#         fluid_factory (FluidFactoryInterface | list[FluidFactoryInterface] | None): the fluid factory instance describing compositional properties for the process fluid.
#         power_loss_factor (TimeSeriesPowerLossFactor | None): expression for power loss factor.
#         suction_pressure_expression (TimeSeriesPressure | None): expression for the inlet (suction) pressure.
#         discharge_pressure_expression (TimeSeriesPressure | None): expression for the outlet (discharge) pressure.
#         intermediate_pressure_expression (TimeSeriesPressure | None): expression for intermediate pressure.
#     """
#
#     def __init__(
#         self,
#         rate_expression: TimeSeriesFlowRate | list[TimeSeriesFlowRate],
#         fluid_factory: FluidFactoryInterface | list[FluidFactoryInterface],
#         suction_pressure_expression: TimeSeriesPressure,
#         discharge_pressure_expression: TimeSeriesPressure,
#         power_loss_factor: TimeSeriesPowerLossFactor | None = None,
#         intermediate_pressure_expression: TimeSeriesPressure | None = None,
#     ):
#         self._rate_expression = rate_expression
#         self._fluid_factory = fluid_factory
#         self._power_loss_factor = power_loss_factor
#         self._suction_pressure_expression = suction_pressure_expression
#         self._discharge_pressure_expression = discharge_pressure_expression
#         self._intermediate_pressure_expression = intermediate_pressure_expression
#
#     @property
#     def power_loss_factor(self) -> TimeSeriesPowerLossFactor | None:
#         return self._power_loss_factor
#
#     @property
#     def periods(self) -> Periods:
#         if isinstance(self._rate_expression, list):
#             return self._rate_expression[0].get_periods()
#         return self._rate_expression.get_periods()
#
#     def apply_to_model(self, compressor_model: CompressorTrainModel | CompressorWithTurbineModel):
#         rate_expr = self._rate_expression if isinstance(self._rate_expression, list) else [self._rate_expression]
#
#         if not isinstance(compressor_model, CompressorTrainCommonShaftMultipleStreamsAndPressures):
#             assert len(rate_expr) == 1
#             stream_day_rate = np.asarray(rate_expr[0].get_stream_day_values(), dtype=np.float64)
#         else:
#             stream_day_rate = np.array([rate.get_stream_day_values() for rate in rate_expr], dtype=np.float64)
#
#         intermediate_pressure = (
#             np.asarray(self._intermediate_pressure_expression.get_values(), dtype=np.float64)
#             if self._intermediate_pressure_expression is not None
#             else None
#         )
#         suction_pressure = np.asarray(self._suction_pressure_expression.get_values(), dtype=np.float64)
#         discharge_pressure = np.asarray(self._discharge_pressure_expression.get_values(), dtype=np.float64)
#
#         compressor_model.set_evaluation_input(
#             rate=stream_day_rate,
#             fluid_factory=self._fluid_factory,
#             suction_pressure=suction_pressure,
#             discharge_pressure=discharge_pressure,
#             intermediate_pressure=intermediate_pressure,
#         )


class CompressorSampledEvaluationInput:
    """
    Encapsulates all input data required to configure and apply evaluation parameters to a sampled compressor model.

    Attributes:
        rate_expression (TimeSeriesFlowRate | list[TimeSeriesFlowRate]): the flow rate expression(s).
        power_loss_factor (TimeSeriesPowerLossFactor | None): expression for power loss factor.
        suction_pressure_expression (TimeSeriesPressure | None): expression for the inlet (suction) pressure.
        discharge_pressure_expression (TimeSeriesPressure | None): expression for the outlet (discharge) pressure.
    """

    def __init__(
        self,
        rate_expression: TimeSeriesFlowRate | list[TimeSeriesFlowRate],
        power_loss_factor: TimeSeriesPowerLossFactor | None = None,
        suction_pressure_expression: TimeSeriesPressure | None = None,
        discharge_pressure_expression: TimeSeriesPressure | None = None,
    ):
        self._rate_expression = rate_expression
        self._power_loss_factor = power_loss_factor
        self._suction_pressure_expression = suction_pressure_expression
        self._discharge_pressure_expression = discharge_pressure_expression

    @property
    def power_loss_factor(self) -> TimeSeriesPowerLossFactor | None:
        return self._power_loss_factor

    @property
    def periods(self) -> Periods:
        if isinstance(self._rate_expression, list):
            return self._rate_expression[0].get_periods()
        return self._rate_expression.get_periods()

    def apply_to_model(self, compressor_model: CompressorModelSampled | CompressorWithTurbineModel):
        rate_expr = [self._rate_expression]

        assert len(rate_expr) == 1
        stream_day_rate = np.asarray(rate_expr[0].get_stream_day_values(), dtype=np.float64)

        suction_pressure = (
            np.asarray(self._suction_pressure_expression.get_values(), dtype=np.float64)
            if self._suction_pressure_expression is not None
            else None
        )
        discharge_pressure = (
            np.asarray(self._discharge_pressure_expression.get_values(), dtype=np.float64)
            if self._discharge_pressure_expression is not None
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

    @property
    def rate(self) -> NDArray[np.float64]:
        return np.asarray(self._rate.get_stream_day_values(), dtype=np.float64)

    @property
    def suction_pressure(self) -> NDArray[np.float64]:
        return np.asarray(self._suction_pressure.get_values(), dtype=np.float64)

    @property
    def discharge_pressure(self) -> NDArray[np.float64]:
        return np.asarray(self._discharge_pressure.get_values(), dtype=np.float64)

    @property
    def fluid_density(self) -> NDArray[np.float64]:
        return np.asarray(self._fluid_density.get_values(), dtype=np.float64)

    def apply_to_model(self, pump_model: PumpModel):
        stream_day_rate = np.asarray(self._rate.get_stream_day_values(), dtype=np.float64)

        pump_model.set_evaluation_input(
            stream_day_rate=stream_day_rate,
            suction_pressure=np.asarray(self._suction_pressure.get_values(), dtype=np.float64),
            discharge_pressure=np.asarray(self._discharge_pressure.get_values(), dtype=np.float64),
            fluid_density=np.asarray(self._fluid_density.get_values(), dtype=np.float64),
        )

    def get_single_time_step_inputs(self) -> list[PumpEvaluationInputSingleTimeStep]:
        n_timesteps = self.rate.shape[0]
        result = []
        for i in range(n_timesteps):
            result.append(
                PumpEvaluationInputSingleTimeStep(
                    rate=self.rate[i],
                    suction_pressure=self.suction_pressure[i],
                    discharge_pressure=self.discharge_pressure[i],
                    fluid_density=self.fluid_density[i],
                )
            )
        return result
