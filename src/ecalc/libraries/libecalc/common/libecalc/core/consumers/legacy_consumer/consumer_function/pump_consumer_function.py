from typing import List, Union

import numpy as np
from libecalc.common.utils.rates import Rates
from libecalc.core.consumers.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.core.consumers.legacy_consumer.consumer_function.utils import (
    calculate_energy_usage_with_conditions_and_power_loss,
)
from libecalc.core.models.pump import PumpModel
from libecalc.dto import VariablesMap
from libecalc.expression import Expression


class PumpConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        pump_function: Union[PumpModel],
        rate_expression: Expression,
        suction_pressure_expression: Expression,
        discharge_pressure_expression: Expression,
        fluid_density_expression: Expression,
        condition_expression: Expression = None,
        power_loss_factor_expression: Expression = None,
    ):
        self._pump_function = pump_function
        self._rate_expression = rate_expression
        self._suction_pressure_expression = suction_pressure_expression
        self._discharge_pressure_expression = discharge_pressure_expression
        self._fluid_density_expression = fluid_density_expression

        self._condition_expression = condition_expression
        # Typically used for power line loss subsea et.c.
        self._power_loss_factor_expression = power_loss_factor_expression

    def evaluate(
        self,
        variables_map: VariablesMap,
        regularity: List[float],
    ) -> ConsumerFunctionResult:
        calendar_day_rate = self._rate_expression.evaluate(
            variables=variables_map.variables, fill_length=len(variables_map.time_vector)
        )
        # if regularity is 0 for a calendar day rate, set stream day rate to 0 for that step
        stream_day_rate = Rates.to_stream_day(
            calendar_day_rates=calendar_day_rate,
            regularity=regularity,
        )
        suction_pressure = self._suction_pressure_expression.evaluate(
            variables=variables_map.variables, fill_length=len(variables_map.time_vector)
        )
        discharge_pressure = self._discharge_pressure_expression.evaluate(
            variables=variables_map.variables, fill_length=len(variables_map.time_vector)
        )
        fluid_density = self._fluid_density_expression.evaluate(
            variables=variables_map.variables, fill_length=len(variables_map.time_vector)
        )

        # Do not input regularity to pump function. Handled outside
        energy_function_result = self._pump_function.evaluate_rate_ps_pd_density(
            rate=stream_day_rate,
            suction_pressures=suction_pressure,
            discharge_pressures=discharge_pressure,
            fluid_density=fluid_density,
        )

        conditions_and_power_loss_results = calculate_energy_usage_with_conditions_and_power_loss(
            variables_map=variables_map,
            energy_usage=np.asarray(energy_function_result.energy_usage),
            condition_expression=self._condition_expression,
            power_loss_factor_expression=self._power_loss_factor_expression,
        )
        pump_consumer_function_result = ConsumerFunctionResult(
            time_vector=np.array(variables_map.time_vector),
            is_valid=np.asarray(energy_function_result.is_valid),
            energy_function_result=energy_function_result,
            energy_usage_before_conditioning=np.asarray(energy_function_result.energy_usage),
            condition=conditions_and_power_loss_results.condition,
            energy_usage_before_power_loss_factor=conditions_and_power_loss_results.energy_usage_after_condition_before_power_loss_factor,
            power_loss_factor=conditions_and_power_loss_results.power_loss_factor,
            energy_usage=conditions_and_power_loss_results.resulting_energy_usage,
        )
        return pump_consumer_function_result
