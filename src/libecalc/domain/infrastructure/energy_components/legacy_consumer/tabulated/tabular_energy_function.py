from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import numpy as np

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import InvalidColumnException
from libecalc.common.interpolation import setup_interpolator_1d, setup_interpolator_n_dimensional
from libecalc.common.list.adjustment import transform_linear
from libecalc.domain.component_validation_error import (
    ModelValidationError,
    ProcessEqualLengthValidationException,
    ProcessHeaderValidationException,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated.common import Variable
from libecalc.presentation.yaml.validation_errors import Location


class TabularEnergyFunction:
    """
    Provides interpolation of energy usage from tabular data for a set of variables.

    This class validates and stores tabular input data, sets up a one- or multidimensional
    interpolation function for energy usage, and provides an interface for interpolating
    energy usage values based on input variables.

    The class supports both POWER and FUEL energy usage types, and applies optional
    adjustment constants and factors to the interpolated values.

    Public methods include:
      - interpolate: Interpolates energy usage for given variable values.
      - get_column: Returns the data column for a specified header.
      - get_energy_usage_type: Returns the energy usage type (POWER or FUEL).
      - get_function_values: Retrieves the energy usage values from the data.
      - get_variables: Returns a dictionary of variable names and their data.
      - validate_headers: Validates that headers include POWER or FUEL.
      - validate_data: Ensures all data columns are numeric and of equal length.
    """

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
        # If function_values_adjusted can be a float, convert it to a 0-dim array:
        if isinstance(function_values_adjusted, float):
            function_values_adjusted = np.array([function_values_adjusted])

        self._func = self._setup_interpolator(variables, function_values_adjusted)
        self.energy_usage_type = self.get_energy_usage_type()

    def interpolate(self, variables_array: np.ndarray) -> np.ndarray:
        """
        Public method to interpolate energy usage.
        Args:
            variables_array: np.ndarray of variable values, shape (n_points, n_variables) or (n_variables,)
        Returns:
            np.ndarray: Interpolated energy usage values.
        """
        return self._func(variables_array)

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
        """
        Ensures all data columns are numeric and of equal length.

        Raises:
            ProcessEqualLengthValidationException: If column lengths differ.
            InvalidColumnException: If non-numeric data is found.
        """

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
                        header=header, message=f"Got non-numeric value '{value}'.", row_index=row_index
                    ) from e

    @staticmethod
    def _setup_interpolator(variables: list[Variable], function_values_adjusted: np.ndarray) -> Callable:
        """
        Sets up a 1D or multidimensional interpolator for the given variables and function values.

        Args:
            variables (list[Variable]): Variables to interpolate over.
            function_values_adjusted (np.ndarray): Adjusted energy usage values.

        Returns:
            Callable: Interpolator function.
        """

        if len(variables) == 1:
            return setup_interpolator_1d(
                variable=np.array(variables[0].values),
                function_values=np.array(function_values_adjusted),
                fill_value=np.nan,
                bounds_error=False,
            )
        else:
            return setup_interpolator_n_dimensional(
                variables=[np.array(v.values) for v in variables],
                function_values=np.array(function_values_adjusted),
                fill_value=np.nan,
                rescale=True,
            )
