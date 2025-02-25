import numpy as np

from libecalc.common.list.list_utils import array_to_list
from libecalc.common.utils.rates import Rates
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.utils import (
    apply_condition,
    apply_power_loss_factor,
    get_condition_from_expression,
    get_power_loss_factor_from_expression,
)
from libecalc.domain.process.core.tabulated import (
    ConsumerTabularEnergyFunction,
    Variable,
    VariableExpression,
)
from libecalc.expression import Expression


class TabulatedConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        tabulated_energy_function: ConsumerTabularEnergyFunction,
        variables_expressions: list[VariableExpression],
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
        expression_evaluator: ExpressionEvaluator,
        regularity: list[float],
    ) -> ConsumerFunctionResult:
        """Evaluate the ConsumerFunction to get energy usage [MW] or [Sm3/day] (electricity or fuel)."""
        variables_for_calculation = {
            variable.name: Variable(
                name=variable.name,
                values=expression_evaluator.evaluate(expression=variable.expression),
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

        condition = get_condition_from_expression(
            condition_expression=self._condition_expression,
            expression_evaluator=expression_evaluator,
        )
        # for tabular, is_valid is based on energy_usage being NaN. This will also (correctly) change potential
        # invalid points to valid where the condition sets energy_usage to zero
        energy_function_result.energy_usage = array_to_list(
            apply_condition(
                input_array=np.asarray(energy_function_result.energy_usage),
                condition=condition,
            )
        )
        energy_function_result.power = (
            array_to_list(
                apply_condition(
                    input_array=np.asarray(energy_function_result.power),
                    condition=condition,
                )
            )
            if energy_function_result.power is not None
            else None
        )

        power_loss_factor = get_power_loss_factor_from_expression(
            expression_evaluator=expression_evaluator,
            power_loss_factor_expression=self._power_loss_factor_expression,
        )

        return ConsumerFunctionResult(
            periods=expression_evaluator.get_periods(),
            is_valid=np.asarray(energy_function_result.is_valid),
            energy_function_result=energy_function_result,
            condition=condition,
            energy_usage_before_power_loss_factor=np.asarray(energy_function_result.energy_usage),
            power_loss_factor=power_loss_factor,
            energy_usage=apply_power_loss_factor(
                energy_usage=np.asarray(energy_function_result.energy_usage),
                power_loss_factor=power_loss_factor,
            ),
        )
