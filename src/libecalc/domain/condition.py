import numpy as np
from numpy._typing import NDArray

from libecalc.common.variables import ExpressionEvaluator
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression.expression import ExpressionType


class Condition:
    """
    Represents a condition that can be applied to arrays based on an expression.

    The Condition class encapsulates logic for evaluating a condition expression
    and applying it to numerical arrays, typically to mask or zero out values
    where the condition is not met.

    Attributes:
        _expression_input (ExpressionType | None): The raw input for the condition expression.
        expression: The parsed and validated expression, or None if not provided.
    """

    def __init__(
        self,
        expression_input: ExpressionType | None,
    ):
        self._expression_input = expression_input
        self.expression = convert_expression(self._expression_input)

    def as_vector(
        self,
        expression_evaluator: ExpressionEvaluator,
    ) -> NDArray[np.int_] | None:
        """
        Evaluate the condition expression and return a vector indicating where the condition is met.

        Args:
            expression_evaluator (ExpressionEvaluator): Evaluator for variable and condition expressions.

        Returns:
            NDArray[np.int_] | None: An integer array (1 where condition is true, 0 otherwise),
            or None if no condition is set.
        """
        if self.expression is None:
            return None

        condition = expression_evaluator.evaluate(expression=self.expression)
        condition = (condition != 0).astype(int)

        return np.array(condition)

    def _apply(
        self, input_array: NDArray[np.float64], expression_evaluator: ExpressionEvaluator
    ) -> NDArray[np.float64]:
        """
        Internal method containing the core logic for applying the condition to an array.
        This method performs the actual masking/zeroing operation based on the condition:

        - Keeps values where condition is true (1)
        - Sets values to 0 where condition is false

        Args:
            input_array (NDArray[np.float64]): The array to apply the condition to.
            expression_evaluator (ExpressionEvaluator): Evaluator for the condition expression.

        Returns:
            NDArray[np.float64]: The resulting array after applying the condition.

        """
        condition_vector = self.as_vector(expression_evaluator)
        if condition_vector is None:
            return input_array.copy()
        return np.where(condition_vector, input_array, 0)

    def apply_to_array(self, input_array: np.ndarray, expression_evaluator: ExpressionEvaluator) -> np.ndarray:
        """
        Convenience method for applying the condition and returning the result as a Python list.

        This is useful when a standard Python list is required . Internally, it calls `_apply`
        and converts the result to a list.
        """

        return self._apply(input_array, expression_evaluator)

    def apply_to_array_as_list(self, input_array: np.ndarray, expression_evaluator: ExpressionEvaluator) -> list:
        """
        Apply the condition to a numpy array and return the result as a Python list.

        This method is a convenience wrapper around `apply_to_array` for cases where a standard
        Python list is needed instead of a numpy array, for example when serializing results
        or interfacing with code that does not use numpy.
        """

        return self._apply(input_array, expression_evaluator).tolist()
