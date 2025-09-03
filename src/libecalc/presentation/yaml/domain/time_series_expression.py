import numpy as np

from libecalc.common.variables import ExpressionEvaluator
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression.expression import Expression, ExpressionType
from libecalc.presentation.yaml.domain.time_series_mask import TimeSeriesMask


class TimeSeriesExpression:
    """
    Handles and evaluates a time series expression.
    """

    def __init__(
        self,
        expression: ExpressionType,
        expression_evaluator: ExpressionEvaluator,
        condition: ExpressionType | None = None,
    ):
        """
        Initializes the TimeSeriesExpression with an expressions and an evaluator.

        Args:
            expression (ExpressionType): A single expression.
            expression_evaluator (ExpressionEvaluator): An instance used to evaluate the expression.

        """

        self._expression = convert_expression(expression)
        self.expression_evaluator = expression_evaluator
        self._condition = convert_expression(condition) if condition is not None else None

    def get_expression(self) -> Expression:
        """
        Returns the converted expression.
        """
        return self._expression

    def get_evaluated_expression(self) -> list[float]:
        """
        Evaluates expression and returns the result as a NumPy array.
        """

        # Check if there is an expression to evaluate
        if self._expression is None:
            return None

        values = self.expression_evaluator.evaluate(expression=self._expression)
        arr = np.array(values)

        if arr.shape[0] == 1:
            arr = np.atleast_1d(arr[0])  # Flattens (1, N) to (N,)
        return arr.tolist()

    def get_masked_values(self) -> list[float]:
        """
        Returns the evaluated expressions with the condition mask applied.
        """
        values = np.asarray(self.get_evaluated_expression(), dtype=np.float64)
        mask = self.get_condition_mask()
        masked = mask.apply(values)
        return masked.tolist()

    def get_condition_mask(self) -> TimeSeriesMask:
        mask = self.expression_evaluator.evaluate(expression=self._condition) if self._condition is not None else None
        return TimeSeriesMask.from_array(mask)
