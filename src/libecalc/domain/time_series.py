import numpy as np

from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.interfaces.time_series_interface import TimeSeriesInterface
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression.expression import ExpressionType


class TimeSeries(TimeSeriesInterface):
    def __init__(
        self,
        expression: ExpressionType | list[ExpressionType],
        expression_evaluator: ExpressionEvaluator,
    ):
        if isinstance(expression, list):
            self._expressions = [convert_expression(expr) for expr in expression]
        else:
            self._expressions = [convert_expression(expression)]
        self._expression_evaluator = expression_evaluator

    def get_values_array(self) -> np.ndarray:
        """
        Returns the time series values as a NumPy array.

        If there are no expressions or the first expression is None,
        returns an empty array. If there is only one expression,
        returns its evaluated value directly (not as a 1D array).
        Otherwise, returns a 1D array of evaluated values.
        """
        # Check if there are any expressions to evaluate
        # Filter out None expressions
        expressions = [expr for expr in self._expressions if expr is not None]

        if not expressions:
            return np.array([], dtype=np.float64)
        # Evaluate all expressions and collect the results
        values = [self._expression_evaluator.evaluate(expression=expr) for expr in expressions]
        arr = np.array(values)

        # Return 1D array if only one expression
        if arr.shape[0] == 1:
            return arr[0]
        return arr

    def get_values_list(self) -> list[float]:
        """
        Returns the time series values as a list of floats.
        """
        arr = self.get_values_array()
        if arr is None:
            return []
        return np.atleast_1d(arr).tolist()

    def get_expression(self, index: int = 0):
        """Returns the Expression at the given index (default: first)."""
        return self._expressions[index]
