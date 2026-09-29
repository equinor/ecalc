"""Reimplements legacy's TABULAR energy usage model: interpolates a single energy usage
value (FUEL or POWER) from a table of arbitrary named variables. Unlike SampledCompressor,
there is no convex-hull extrapolation here - a query outside the sample points' envelope
returns NaN, matching legacy's TabularEnergyFunction. Reuses the same interpolation setup
as legacy (libecalc.common.interpolation), which has no libecalc.domain dependency.
"""

from collections.abc import Mapping, Sequence

import numpy as np
from scipy.spatial import QhullError

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.interpolation import setup_interpolator


class TabularModel:
    """A named-variable table (variables -> a single energy usage value), built once and
    evaluated at as many operating points as needed."""

    def __init__(
        self,
        variables: Mapping[str, Sequence[float]],
        function_values: Sequence[float],
        function_name: str = "function_values",
    ) -> None:
        self.variables = dict(variables)
        self.function_values = function_values
        self.function_name = function_name
        self._validate()
        self._variable_names = tuple(self.variables)
        rows = self._unique_rows()
        self._require_enough_rows(len(rows))
        try:
            self._interpolator = setup_interpolator(
                variables=[rows[:, index] for index in range(len(self.variables))],
                function_values=rows[:, -1],
            )
        except (QhullError, ValueError) as error:
            raise EcalcValidationException(
                "Could not interpolate the table. The sample points must span every variable, "
                "i.e. not lie on a line or plane."
            ) from error

    def get_variable_names(self) -> tuple[str, ...]:
        return self._variable_names

    def evaluate(self, variables: Mapping[str, float]) -> float:
        missing = [name for name in self._variable_names if name not in variables]
        if missing:
            raise IllegalStateException(f"Missing value(s) for variable(s): {', '.join(missing)}.")
        point = [variables[name] for name in self._variable_names]
        result = self._interpolator(point[0]) if len(point) == 1 else self._interpolator(point)
        return float(np.asarray(result).reshape(-1)[0])

    def _validate(self) -> None:
        if not self.variables:
            raise EcalcValidationException("Need at least one variable for TabularModel.")
        count = len(self.function_values)
        for name, values in self.variables.items():
            if len(values) != count:
                raise EcalcValidationException(
                    f"{name} has {len(values)} values, but {self.function_name} has {count}. All columns must be equally long."
                )
        for name, values in (*self.variables.items(), (self.function_name, self.function_values)):
            if not np.all(np.isfinite(np.asarray(values, dtype=np.float64))):
                raise EcalcValidationException(f"Column {name} has a non-finite value (NaN or infinity).")
        if np.any(np.asarray(self.function_values, dtype=np.float64) < 0):
            raise EcalcValidationException(f"Column {self.function_name} has a negative value.")

    def _require_enough_rows(self, count: int) -> None:
        min_rows = len(self.variables) + 1
        if count < min_rows:
            raise EcalcValidationException(
                f"Need at least {min_rows} unique rows to interpolate {len(self.variables)} variable(s), got {count}."
            )

    def _unique_rows(self) -> np.ndarray:
        """Rows of [*variables, function_value] without exact duplicates; conflicting duplicates are rejected."""
        rows = np.unique(
            np.column_stack(
                [np.asarray(values, dtype=np.float64) for values in (*self.variables.values(), self.function_values)]
            ),
            axis=0,
        )
        if len(np.unique(rows[:, :-1], axis=0)) != len(rows):
            raise EcalcValidationException("The same variable values are given more than once with different results.")
        return rows
