from __future__ import annotations

from typing import Literal

import numpy as np
from scipy.interpolate import LinearNDInterpolator, interp1d

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import IllegalStateException, InvalidColumnException
from libecalc.common.list.adjustment import transform_linear
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.component_validation_error import (
    ModelValidationError,
    ProcessEqualLengthValidationException,
    ProcessHeaderValidationException,
)
from libecalc.domain.process.core.results.base import EnergyFunctionResult
from libecalc.expression import Expression
from libecalc.presentation.yaml.validation_errors import Location


class TabularEnergyFunction:
    typ: Literal[EnergyModelType.TABULATED] = EnergyModelType.TABULATED

    def __init__(
        self,
        headers: list[str],
        data: list[list[float]],
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
    ):
        self.headers = headers
        self.data = data
        self.energy_usage_adjustment_constant = energy_usage_adjustment_constant
        self.energy_usage_adjustment_factor = energy_usage_adjustment_factor
        self.validate_headers()
        self.validate_data()

        """Tabular consumer energy function [MW] or [Sm3/day]."""
        function_values = self.get_function_values()
        variables = [Variable(name=name, values=values) for name, values in self.get_variables().items()]

        self.required_variables = [variable.name for variable in variables]
        function_values_adjusted = transform_linear(
            values=np.reshape(np.asarray(function_values), -1),
            constant=self.energy_usage_adjustment_constant,
            factor=self.energy_usage_adjustment_factor,
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
        self.energy_usage_type = self.get_energy_usage_type()

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

    def get_column(self, header: str) -> list:
        return self.data[self.headers.index(header)]

    def get_energy_usage_type(self) -> EnergyUsageType:
        return EnergyUsageType.POWER if EnergyUsageType.POWER.value in self.headers else EnergyUsageType.FUEL

    def _get_function_value_header(self) -> str:
        return self.get_energy_usage_type().value

    def get_function_values(self) -> list[float]:
        return self.get_column(self._get_function_value_header())

    def get_variables(self) -> {str, list[float]}:
        variable_headers = [header for header in self.headers if header != self._get_function_value_header()]
        return {header: self.get_column(header) for header in variable_headers}

    def validate_headers(self):
        is_valid_headers = len(self.headers) > 0 and ("FUEL" in self.headers or "POWER" in self.headers)
        if not is_valid_headers:
            msg = "TABULAR facility input type data must have a 'FUEL' or 'POWER' header"

            raise ProcessHeaderValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

    def validate_data(self):
        lengths = [len(lst) for lst in self.data]
        if len(set(lengths)) > 1:
            problematic_vectors = [(i, len(lst)) for i, lst in enumerate(self.data)]
            msg = f"TABULAR facility input type data should have equal number of datapoints for all headers. Found lengths: {problematic_vectors}"

            raise ProcessEqualLengthValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )
        for column_index, header in enumerate(self.headers):
            for row_index, value in enumerate(self.data[column_index]):
                try:
                    float(value)
                except ValueError as e:
                    raise InvalidColumnException(
                        header=header, message=f"Got non-numeric value '{value}'.", row=row_index
                    ) from e


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
