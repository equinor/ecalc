from typing import List

import numpy as np
from libecalc.common.utils.rates import Rates
from libecalc.core.consumers.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.core.consumers.legacy_consumer.consumer_function.utils import (
    calculate_energy_usage_with_conditions_and_power_loss,
)
from libecalc.core.models.tabulated import (
    ConsumerTabularEnergyFunction,
    Variable,
    VariableExpression,
)
from libecalc.dto import VariablesMap
from libecalc.expression import Expression


class TabulatedConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        tabulated_energy_function: ConsumerTabularEnergyFunction,
        variables_expressions: List[VariableExpression],
        condition_expression: Expression = None,
        power_loss_factor_expression: Expression = None,
    ):
        """Tabulated consumer function [MW] (energy) or [Sm3/day] (fuel)."""
        # Consistency of variables between tabulated_energy_function and variables_expressions must be validated up
        # front
        self._tabulated_energy_function = tabulated_energy_function
        self._variables_expressions = variables_expressions

        self._condition_expression = condition_expression
        # Typically used for power line loss subsea et.c.
        self._power_loss_factor_expression = power_loss_factor_expression

    def evaluate(
        self,
        variables_map: VariablesMap,
        regularity: List[float],
    ) -> ConsumerFunctionResult:
        """Evaluate the ConsumerFunction to get energy usage [MW] or [Sm3/day] (electricity or fuel)."""
        variables_for_calculation = {
            variable.name: Variable(
                name=variable.name,
                values=variable.expression.evaluate(
                    variables=variables_map.variables, fill_length=len(variables_map.time_vector)
                ),
            )
            for variable in self._variables_expressions
        }
        # If some of these are rates, we need to calculate stream day rate for use
        # Also take a copy of the calendar day rate and stream day rate for input to result object
        for variable_name, variable in variables_for_calculation.items():
            if variable_name.lower() == "rate":
                stream_day_rate = Rates.to_stream_day(
                    calendar_day_rates=variable.values,
                    regularity=regularity,
                )
                variables_for_calculation[variable_name] = Variable(name=variable_name, values=stream_day_rate)

        energy_function_result = self._tabulated_energy_function.evaluate_variables(
            variables=list(variables_for_calculation.values()),
        )

        conditions_and_power_loss_results = calculate_energy_usage_with_conditions_and_power_loss(
            variables_map=variables_map,
            energy_usage=np.asarray(energy_function_result.energy_usage),
            condition_expression=self._condition_expression,
            power_loss_factor_expression=self._power_loss_factor_expression,
        )

        tabulated_consumer_function_result = ConsumerFunctionResult(
            time_vector=np.array(variables_map.time_vector),
            is_valid=np.asarray(energy_function_result.is_valid),
            energy_function_result=energy_function_result,
            energy_usage_before_conditioning=np.asarray(energy_function_result.energy_usage),
            condition=conditions_and_power_loss_results.condition,
            energy_usage_before_power_loss_factor=conditions_and_power_loss_results.energy_usage_after_condition_before_power_loss_factor,
            # noqa
            power_loss_factor=conditions_and_power_loss_results.power_loss_factor,
            energy_usage=conditions_and_power_loss_results.resulting_energy_usage,
        )

        return tabulated_consumer_function_result
