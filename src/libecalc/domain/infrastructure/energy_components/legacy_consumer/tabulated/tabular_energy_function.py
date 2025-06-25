from __future__ import annotations

import numpy as np
from scipy.interpolate import LinearNDInterpolator, interp1d

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.list.adjustment import transform_linear
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.process.core.results.base import EnergyFunctionResult
from libecalc.domain.process.dto import TabulatedData
from libecalc.expression import Expression


class ConsumerTabularEnergyFunction:
    def __init__(
        self,
        energy_model: TabulatedData,
    ):
        """Tabular consumer energy function [MW] or [Sm3/day]."""
        function_values = energy_model.get_function_values()
        variables = [Variable(name=name, values=values) for name, values in energy_model.get_variables().items()]

        self.required_variables = [variable.name for variable in variables]
        function_values_adjusted = transform_linear(
            values=np.reshape(np.asarray(function_values), -1),
            constant=energy_model.energy_usage_adjustment_constant,
            factor=energy_model.energy_usage_adjustment_factor,
        )
        if len(variables) == 1:
            self._func = interp1d(
                x=np.reshape(variables[0].values, -1),
                y=np.reshape(function_values_adjusted, -1),
                fill_value=np.nan,
                bounds_error=False,
            )
        else:
            self._func = LinearNDInterpolator(
                np.asarray([variable.values for variable in variables]).transpose(),
                function_values_adjusted,
                fill_value=np.nan,
                rescale=True,
            )
        self.energy_usage_type = energy_model.get_energy_usage_type()

    def evaluate_variables(self, variables: list[Variable]) -> EnergyFunctionResult:
        variables_map_by_name = {variable.name: variable.values for variable in variables}
        _check_variables_match_required(
            variables_to_evaluate=list(variables_map_by_name.keys()), required_variables=self.required_variables
        )
        variables_array_for_evaluation = np.asarray(
            [variables_map_by_name.get(variable_name) for variable_name in self.required_variables]
        )
        variables_array_for_evaluation = np.squeeze(variables_array_for_evaluation)  # Remove empty dimensions
        variables_array_for_evaluation = np.transpose(variables_array_for_evaluation)
        energy_usage = self._func(variables_array_for_evaluation)

        energy_usage_list = array_to_list(energy_usage)
        if energy_usage_list is None:
            energy_usage_list = []  # Provide empty list as fallback

        return EnergyFunctionResult(
            energy_usage=energy_usage_list,
            energy_usage_unit=Unit.MEGA_WATT
            if self.energy_usage_type == EnergyUsageType.POWER
            else Unit.STANDARD_CUBIC_METER_PER_DAY,
            power=energy_usage_list if self.energy_usage_type == EnergyUsageType.POWER else None,
            power_unit=Unit.MEGA_WATT if self.energy_usage_type == EnergyUsageType.POWER else None,
        )


def _check_variables_match_required(variables_to_evaluate: list[str], required_variables: list[str]):
    if set(variables_to_evaluate) != set(required_variables):
        msg = (
            "Variables to evaluate must correspond to required variables. You should not end up"
            " here, please contact support."
        )
        logger.exception(msg)
        raise IllegalStateException(msg)


class VariableExpression:
    def __init__(self, name: str, expression: Expression):
        self.name = name
        self.expression = expression


class Variable:
    def __init__(self, name: str, values: list[float]):
        self.name = name
        self.values = values
