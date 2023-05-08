from typing import List, Optional, Union

import numpy as np
from libecalc.common.utils.rates import Rates
from libecalc.core.consumers.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.core.consumers.legacy_consumer.consumer_function.utils import (
    calculate_energy_usage_with_conditions_and_power_loss,
)
from libecalc.core.models.compressor.base import CompressorModel
from libecalc.core.models.compressor.train.variable_speed_compressor_train_common_shaft_multiple_streams_and_pressures import (
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.core.models.results import CompressorTrainResult
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression


class CompressorConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        compressor_function: CompressorModel,
        rate_expression: Union[Expression, List[Expression]],
        suction_pressure_expression: Expression,
        discharge_pressure_expression: Expression,
        condition_expression: Optional[Expression],
        power_loss_factor_expression: Optional[Expression],
        intermediate_pressure_expression: Optional[Expression] = None,
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
        self._compressor_function = compressor_function
        self._rate_expression = rate_expression if isinstance(rate_expression, list) else [rate_expression]
        self._suction_pressure_expression = suction_pressure_expression
        self._discharge_pressure_expression = discharge_pressure_expression
        self._condition_expression = condition_expression
        self._power_loss_factor_expression = power_loss_factor_expression
        self._intermediate_pressure_expression = intermediate_pressure_expression

    def evaluate(
        self,
        variables_map: VariablesMap,
        regularity: List[float],
    ) -> ConsumerFunctionResult:
        """Evaluate the Compressor energy usage.
        :param variables_map: Variables map is the VariablesMap-object holding all the data to be evaluated.
        :param regularity:
        :return:
        """
        calendar_day_rates = np.array(
            [
                rate_expression.evaluate(variables=variables_map.variables, fill_length=len(variables_map.time_vector))
                for rate_expression in self._rate_expression
            ]
        )
        # Squeeze to remove axes of length one -> non-multiple streams will be 1d and not 2d.
        # But we don't want to squeeze multiple streams model with only one date
        if isinstance(self._compressor_function, VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures):
            stream_day_rate = Rates.to_stream_day(
                calendar_day_rates=calendar_day_rates,
                regularity=regularity,
            )
        else:
            stream_day_rate = np.atleast_1d(
                np.squeeze(
                    Rates.to_stream_day(
                        calendar_day_rates=calendar_day_rates,
                        regularity=regularity,
                    )
                )
            )

        intermediate_pressure = (
            self._intermediate_pressure_expression.evaluate(
                variables=variables_map.variables, fill_length=len(variables_map.time_vector)
            )
            if self._intermediate_pressure_expression
            else None
        )
        suction_pressure = (
            self._suction_pressure_expression.evaluate(
                variables=variables_map.variables, fill_length=len(variables_map.time_vector)
            )
            if self._suction_pressure_expression is not None
            else None
        )
        discharge_pressure = (
            self._discharge_pressure_expression.evaluate(
                variables=variables_map.variables, fill_length=len(variables_map.time_vector)
            )
            if self._discharge_pressure_expression is not None
            else None
        )
        compressor_train_result: CompressorTrainResult
        # Do not input regularity to compressor function. Handled outside
        # intermediate_pressure will only be different from None when we have a MultipleStreamsAndPressures train
        if intermediate_pressure is not None:
            compressor_train_result = self._compressor_function.evaluate_rate_ps_pint_pd(
                rate=stream_day_rate,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
                intermediate_pressure=intermediate_pressure,
            )
        else:
            compressor_train_result = self._compressor_function.evaluate_rate_ps_pd(
                rate=stream_day_rate,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )

        conditions_and_power_loss_results = calculate_energy_usage_with_conditions_and_power_loss(
            variables_map=variables_map,
            energy_usage=np.asarray(compressor_train_result.energy_usage),
            condition_expression=self._condition_expression,
            power_loss_factor_expression=self._power_loss_factor_expression,
            power_usage=np.asarray(compressor_train_result.power)
            if compressor_train_result.power is not None
            else None,
        )

        consumer_function_result = ConsumerFunctionResult(
            time_vector=np.array(variables_map.time_vector),
            is_valid=np.asarray(compressor_train_result.is_valid),
            energy_function_result=compressor_train_result,
            energy_usage_before_conditioning=np.asarray(compressor_train_result.energy_usage),
            condition=conditions_and_power_loss_results.condition,
            energy_usage_before_power_loss_factor=conditions_and_power_loss_results.energy_usage_after_condition_before_power_loss_factor,
            power_loss_factor=conditions_and_power_loss_results.power_loss_factor,
            energy_usage=conditions_and_power_loss_results.resulting_energy_usage,
            power=conditions_and_power_loss_results.resulting_power_usage,
        )
        return consumer_function_result
