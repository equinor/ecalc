import numpy as np

from libecalc.common.utils.rates import Rates
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.condition import Condition
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.power_loss_factor import PowerLossFactor
from libecalc.domain.process.compressor.core.base import CompressorModel, CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.train.variable_speed_compressor_train_common_shaft_multiple_streams_and_pressures import (
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.domain.process.core.results import CompressorTrainResult
from libecalc.domain.regularity import Regularity
from libecalc.domain.time_series import TimeSeries


class CompressorConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        compressor_function: CompressorModel,
        rate: TimeSeries,
        suction_pressure: TimeSeries,
        discharge_pressure: TimeSeries,
        condition: Condition,
        regularity: Regularity,
        power_loss_factor: PowerLossFactor,
        intermediate_pressure: TimeSeries | None = None,
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
        :param condition_expression: Optional condition expression
        :param power_loss_factor_expression: Optional power loss factor expression.
            Typically used for power line loss subsea et.c.
        :param intermediate_pressure_expression: Used for multiple streams and pressures model.
        """
        self.condition = condition
        self.regularity = regularity
        self.power_loss_factor = power_loss_factor
        self._compressor_function = compressor_function
        self.rate = rate
        self.suction_pressure = suction_pressure
        self.discharge_pressure = discharge_pressure
        self.intermediate_pressure = intermediate_pressure

    def evaluate(self, expression_evaluator: ExpressionEvaluator) -> ConsumerFunctionResult:
        """Evaluate the Compressor energy usage.
        :param expression_evaluator: Variables map is the VariablesMap-object holding all the data to be evaluated.
        :param regularity:
        :return:
        """

        # Squeeze to remove axes of length one -> non-multiple streams will be 1d and not 2d.
        # But we don't want to squeeze multiple streams model with only one date.
        # That goes for CompressorWithTurbineModel with a MultipleStreamsAndPressures-train as well
        if isinstance(self._compressor_function, CompressorWithTurbineModel):
            compressor_model = self._compressor_function.compressor_model
        else:
            compressor_model = self._compressor_function
        if isinstance(compressor_model, VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures):
            stream_day_rate = Rates.to_stream_day(
                calendar_day_rates=self.rate.get_values_array(),
                regularity=self.regularity.get_values,
            )
        else:
            stream_day_rate = np.atleast_1d(
                np.squeeze(
                    Rates.to_stream_day(
                        calendar_day_rates=self.rate.get_values_array(),
                        regularity=self.regularity.time_series.values,
                    )
                )
            )

        intermediate_pressure = self.intermediate_pressure.get_values_array() if self.intermediate_pressure else None
        suction_pressure = self.suction_pressure.get_values_array()
        discharge_pressure = self.discharge_pressure.get_values_array()

        # Do conditioning first - set rates to zero if conditions are not met

        stream_day_rate_after_condition = self.condition.apply_to_array(
            input_array=stream_day_rate,
        )

        # If the compressor model is supposed to have stages, make sure they are defined
        # (compressor sampled does not have stages)
        if isinstance(self._compressor_function, CompressorWithTurbineModel):
            self._compressor_function.compressor_model.check_for_undefined_stages(
                rate=stream_day_rate_after_condition,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )
        else:
            self._compressor_function.check_for_undefined_stages(
                rate=stream_day_rate_after_condition,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )

        compressor_train_result: CompressorTrainResult
        # Do not input regularity to compressor function. Handled outside
        # intermediate_pressure will only be different from None when we have a MultipleStreamsAndPressures train
        compressor_train_result = self._compressor_function.evaluate(
            rate=stream_day_rate_after_condition,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            intermediate_pressure=intermediate_pressure,
        )

        power_loss_factor = self.power_loss_factor.as_vector()

        consumer_function_result = ConsumerFunctionResult(
            periods=self.regularity.get_periods,
            is_valid=np.asarray(compressor_train_result.is_valid),
            energy_function_result=compressor_train_result,
            condition=self.condition.as_vector(),
            energy_usage_before_power_loss_factor=np.asarray(compressor_train_result.energy_usage),
            power_loss_factor=power_loss_factor,
            energy_usage=self.power_loss_factor.apply_to_array(
                energy_usage=np.asarray(compressor_train_result.energy_usage),
            ),
            power=self.power_loss_factor.apply_to_array(
                energy_usage=np.asarray(compressor_train_result.power),
            )
            if compressor_train_result.power is not None
            else None,
        )
        return consumer_function_result
