import numpy as np

from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.process.compressor.core.base import CompressorModel, CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.train.variable_speed_compressor_train_common_shaft_multiple_streams_and_pressures import (
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor
from libecalc.domain.time_series_pressure import TimeSeriesPressure


class CompressorConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        compressor_function: CompressorModel,
        rate_expression: TimeSeriesFlowRate | list[TimeSeriesFlowRate],
        suction_pressure_expression: TimeSeriesPressure | None,
        discharge_pressure_expression: TimeSeriesPressure | None,
        power_loss_factor_expression: TimeSeriesPowerLossFactor | None,
        intermediate_pressure_expression: TimeSeriesPressure | None = None,
    ):
        """Note: If multiple streams and pressures, there will be  list of rate-Expressions, and there
            may be specification of intermediate pressure, stage number for intermediate pressure and specific
            pressure control mechanisms for first/last part of that compressor train. Except for that, all
            else is equal between the two compressor trans types.

        The compressor consumer function defining the energy usage.
        :param compressor_function: The compressor model
        :param rate_expression: Rate expression [Sm3/h]
            or a list of rates expressions for multiple streams and pressures.
        :param suction_pressure_expression: Suction pressure expression [bara]
        :param discharge_pressure_expression: Discharge pressure expression [bara]
        :param power_loss_factor_expression: Optional power loss factor expression.
            Typically used for power line loss subsea et.c.
        :param intermediate_pressure_expression: Used for multiple streams and pressures model.
        """
        self._compressor_function = compressor_function
        self._rate_expression = rate_expression if isinstance(rate_expression, list) else [rate_expression]
        assert len(self._rate_expression) > 0
        self._suction_pressure_expression = suction_pressure_expression
        self._discharge_pressure_expression = discharge_pressure_expression
        self._power_loss_factor_expression = power_loss_factor_expression
        self._intermediate_pressure_expression = intermediate_pressure_expression

    @property
    def suction_pressure(self) -> TimeSeriesPressure | None:
        return self._suction_pressure_expression

    @property
    def discharge_pressure(self) -> TimeSeriesPressure | None:
        return self._discharge_pressure_expression

    def evaluate(self) -> ConsumerFunctionResult:
        """Evaluate the Compressor energy usage.
        :param expression_evaluator: Variables map is the VariablesMap-object holding all the data to be evaluated.
        :param regularity:
        :return:
        """
        if isinstance(self._compressor_function, CompressorWithTurbineModel):
            compressor_model = self._compressor_function.compressor_model
        else:
            compressor_model = self._compressor_function

        if not isinstance(compressor_model, VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures):
            assert len(self._rate_expression) == 1
            stream_day_rate = np.asarray(self._rate_expression[0].get_stream_day_values(), dtype=np.float64)
        else:
            stream_day_rate = np.array(
                [rate.get_stream_day_values() for rate in self._rate_expression], dtype=np.float64
            )

        intermediate_pressure = (
            np.asarray(self._intermediate_pressure_expression.get_values(), dtype=np.float64)
            if self._intermediate_pressure_expression is not None
            else None
        )
        suction_pressure = (
            np.asarray(self._suction_pressure_expression.get_values(), dtype=np.float64)
            if self._suction_pressure_expression is not None
            else None
        )
        discharge_pressure = (
            np.asarray(self._discharge_pressure_expression.get_values(), dtype=np.float64)
            if self._suction_pressure_expression is not None
            else None
        )

        # If the compressor model is supposed to have stages, make sure they are defined
        # (compressor sampled does not have stages)
        compressor_model.check_for_undefined_stages(
            rate=stream_day_rate,
            suction_pressure=suction_pressure,  # type: ignore[arg-type]
            discharge_pressure=discharge_pressure,  # type: ignore[arg-type]
        )

        # intermediate_pressure will only be different from None when we have a MultipleStreamsAndPressures train
        compressor_train_result = self._compressor_function.evaluate(
            rate=stream_day_rate,
            suction_pressure=suction_pressure,  # type: ignore[arg-type]
            discharge_pressure=discharge_pressure,  # type: ignore[arg-type]
            intermediate_pressure=intermediate_pressure,
        )

        if self._power_loss_factor_expression is not None:
            energy_usage = self._power_loss_factor_expression.apply(np.asarray(compressor_train_result.energy_usage))
            power = (
                self._power_loss_factor_expression.apply(np.asarray(compressor_train_result.power))
                if compressor_train_result.power is not None
                else None
            )
        else:
            energy_usage = compressor_train_result.energy_usage
            power = compressor_train_result.power

        periods = self._rate_expression[0].get_periods()

        consumer_function_result = ConsumerFunctionResult(
            periods=periods,
            is_valid=np.asarray(compressor_train_result.is_valid),
            energy_function_result=compressor_train_result,
            energy_usage_before_power_loss_factor=np.asarray(compressor_train_result.energy_usage),
            power_loss_factor=np.asarray(self._power_loss_factor_expression.get_values(), dtype=np.float64)
            if self._power_loss_factor_expression is not None
            else None,
            energy_usage=np.asarray(energy_usage),
            power=np.asarray(power) if power is not None else None,
        )
        return consumer_function_result
