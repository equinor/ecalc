import numpy as np
from numpy.typing import NDArray

from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.expression import Expression


def get_condition_from_expression(
    expression_evaluator: ExpressionEvaluator,
    condition_expression: Expression | dict[Period, Expression] | None,
) -> NDArray[np.int_] | None:
    """Evaluate condition expression and compute resulting condition vector.

    Args:
        expression_evaluator (ExpressionEvaluator): Service with all info to evaluate expressions.
        condition_expression: The condition expression

    Returns:
        Assembled condition vector
    """
    if condition_expression is None:
        return None

    condition = expression_evaluator.evaluate(expression=condition_expression)
    condition = (condition != 0).astype(int)

    return np.array(condition)


def apply_condition(
    input_array: NDArray[np.float64], condition: NDArray[np.float64] | NDArray[np.int_] | None
) -> NDArray[np.float64]:
    """Apply condition to input array in the following way:
        - Input values kept as is if condition is 1
        - Input values set to 0 if condition is 0

    Args:
        input_array: Array with input values
        condition: Array of 1 or 0 describing whether conditions are met

    Returns:
        Returns the input_array where conditions are applied (values set to 0 where condition is 0)
    """
    if condition is None:
        return np.array(input_array)
    else:
        return np.where(condition, input_array, 0)
