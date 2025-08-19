import numpy as np

from libecalc.common.variables import ExpressionEvaluator
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression.expression import Expression, ExpressionType


class TimeSeriesExpression:
    """
    Handles and evaluates one or more time series expressions.
    """

    def __init__(
        self,
        expressions: ExpressionType | list[ExpressionType],
        expression_evaluator: ExpressionEvaluator,
        condition: ExpressionType | None = None,
    ):
        """
        Initializes the TimeSeriesExpression with one or more expressions and an evaluator.

        :param expressions: A single expression or a list of expressions.
        :param expression_evaluator: An instance used to evaluate expressions.
        """

        if isinstance(expressions, list):
            self._expressions = [convert_expression(expr) for expr in expressions]
        else:
            self._expressions = [convert_expression(expressions)]
        self.expression_evaluator = expression_evaluator
        self._condition = convert_expression(condition) if condition is not None else None

    def get_expressions(self) -> list[Expression]:
        """
        Returns the list of converted expressions.
        """
        return self._expressions

    def get_evaluated_expressions(self) -> list[float]:
        """
        Evaluates all expressions and returns their results as a NumPy array.
        """

        # Check if there are any expressions to evaluate
        # Filter out None expressions
        expressions = [expr for expr in self._expressions if expr is not None]

        # Evaluate all expressions and collect the results
        values = [self.expression_evaluator.evaluate(expression=expr) for expr in expressions]
        arr = np.array(values)

        if arr.shape[0] == 1:
            arr = np.atleast_1d(arr[0])  # Flattens (1, N) to (N,)
        return arr.tolist()

    def get_condition_mask(self):
        if self._condition is None:
            return None
        mask = self.expression_evaluator.evaluate(expression=self._condition)
        return (np.asarray(mask) != 0).astype(int)
