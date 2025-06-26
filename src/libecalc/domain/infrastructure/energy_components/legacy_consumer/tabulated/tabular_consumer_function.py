import numpy as np

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.units import Unit
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
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated.common import (
    Variable,
    VariableExpression,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated.tabular_energy_function import (
    TabularEnergyFunction,
)
from libecalc.domain.process.core.results import EnergyFunctionResult
from libecalc.expression import Expression


class TabularConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        headers: list[str],
        data: list[list[float]],
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        variables_expressions: list[VariableExpression],
        condition_expression: Expression | None = None,
        power_loss_factor_expression: Expression | None = None,
    ):
        """Tabulated consumer function [MW] (energy) or [Sm3/day] (fuel)."""
        # Consistency of variables between tabulated_energy_function and variables_expressions must be validated up
        # front
        self._tabular_energy_function = TabularEnergyFunction(
            headers=headers,
            data=data,
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
        )
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

        variables_for_calculation = []
        # If some of these are rates, we need to calculate stream day rate for use
        # Also take a copy of the calendar day rate and stream day rate for input to result object
        for variable in self._variables_expressions:
            variable_values = expression_evaluator.evaluate(variable.expression)
            if variable.name.lower() == "rate":
                variable_values = Rates.to_stream_day(
                    calendar_day_rates=variable_values,
                    regularity=regularity,
                )
            variables_for_calculation.append(Variable(name=variable.name, values=variable_values.tolist()))

        energy_function_result = self.evaluate_variables(
            variables=variables_for_calculation,
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
                condition=condition,  # type: ignore[arg-type]
            )
        )
        energy_function_result.power = (
            array_to_list(
                apply_condition(
                    input_array=np.asarray(energy_function_result.power),
                    condition=condition,  # type: ignore[arg-type]
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

    def evaluate_variables(self, variables: list[Variable]) -> EnergyFunctionResult:
        variables_map_by_name = {variable.name: variable.values for variable in variables}
        _check_variables_match_required(
            variables_to_evaluate=list(variables_map_by_name.keys()),
            required_variables=self._tabular_energy_function.required_variables,
        )
        variables_array_for_evaluation = np.asarray(
            [
                variables_map_by_name.get(variable_name)
                for variable_name in self._tabular_energy_function.required_variables
            ]
        )
        variables_array_for_evaluation = np.squeeze(variables_array_for_evaluation)  # Remove empty dimensions
        variables_array_for_evaluation = np.transpose(variables_array_for_evaluation)
        energy_usage = self._tabular_energy_function.interpolate(variables_array_for_evaluation)

        energy_usage_list = array_to_list(energy_usage)
        if energy_usage_list is None:
            energy_usage_list = []  # Provide empty list as fallback

        return EnergyFunctionResult(
            energy_usage=energy_usage_list,
            energy_usage_unit=Unit.MEGA_WATT
            if self._tabular_energy_function.energy_usage_type == EnergyUsageType.POWER
            else Unit.STANDARD_CUBIC_METER_PER_DAY,
            power=energy_usage_list
            if self._tabular_energy_function.energy_usage_type == EnergyUsageType.POWER
            else None,
            power_unit=Unit.MEGA_WATT
            if self._tabular_energy_function.energy_usage_type == EnergyUsageType.POWER
            else None,
        )


def _check_variables_match_required(variables_to_evaluate: list[str], required_variables: list[str]):
    if set(variables_to_evaluate) != set(required_variables):
        msg = (
            "Variables to evaluate must correspond to required variables. You should not end up"
            " here, please contact support."
        )
        logger.exception(msg)
        raise IllegalStateException(msg)
