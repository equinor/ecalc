from __future__ import annotations

from typing import List

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from scipy.interpolate import LinearNDInterpolator, interp1d

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.list.adjustment import transform_linear
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.core.models.base import BaseModel
from libecalc.core.models.results.base import EnergyFunctionResult
from libecalc.core.utils.array_type import PydanticNDArray
from libecalc.dto.types import EnergyUsageType
from libecalc.expression import Expression


class ConsumerTabularEnergyFunction(BaseModel):
    def __init__(
        self,
        function_values: NDArray[np.float64],
        variables: List[Variable],
        energy_usage_adjustment_constant: float = 0.0,
        energy_usage_adjustment_factor: float = 1.0,
        energy_usage_type: EnergyUsageType = EnergyUsageType.POWER,
    ):
        """Tabular consumer energy function [MW] or [Sm3/day].

        :param function_values: array containing the function values
        :param variables: list containing one array per variable with variable values
        :param energy_usage_adjustment_constant: a constant to be added to the computed power
        :param energy_usage_adjustment_factor: a factor to be multiplied to computed power
        """
        # data is a DataFrame with 1 or more headers for variables and one function value header

        self.required_variables = [variable.name for variable in variables]
        function_values_adjusted = transform_linear(
            values=np.reshape(function_values, -1),
            constant=energy_usage_adjustment_constant,
            factor=energy_usage_adjustment_factor,
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
        self.energy_usage_type = energy_usage_type

    def evaluate_variables(self, variables: List[Variable]) -> EnergyFunctionResult:
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

        return EnergyFunctionResult(
            energy_usage=array_to_list(energy_usage),
            energy_usage_unit=Unit.MEGA_WATT
            if self.energy_usage_type == EnergyUsageType.POWER
            else Unit.STANDARD_CUBIC_METER_PER_DAY,
            power=array_to_list(energy_usage) if self.energy_usage_type == EnergyUsageType.POWER else None,
            power_unit=Unit.MEGA_WATT if self.energy_usage_type == EnergyUsageType.POWER else None,
        )


def _check_variables_match_required(variables_to_evaluate: List[str], required_variables: List[str]):
    if set(variables_to_evaluate) != set(required_variables):
        msg = (
            "Variables to evaluate must correspond to required variables. You should not end up"
            " here, please contact support."
        )
        logger.exception(msg)
        raise IllegalStateException(msg)


class VariableExpression(PydanticBaseModel):
    name: str
    expression: Expression


class Variable(PydanticBaseModel):
    name: str
    values: PydanticNDArray
    model_config = ConfigDict(arbitrary_types_allowed=True)
