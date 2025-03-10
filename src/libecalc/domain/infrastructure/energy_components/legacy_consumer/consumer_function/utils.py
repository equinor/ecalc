from copy import deepcopy

import numpy as np
from numpy.typing import NDArray

from libecalc.common.variables import ExpressionEvaluator
from libecalc.expression import Expression


def get_condition_from_expression(
    expression_evaluator: ExpressionEvaluator,
    condition_expression: Expression,
) -> NDArray[np.int_] | None:
    """Evaluate condition expression and compute resulting condition vector.

    Args:
        expression_evaluator (ExpressionEvaluator): Service with all info to evaluate expressions.
        condition_expression: The condition expression

    Returns:
        Assembled condition vector
    """
    if condition_expression is not None:
        condition = expression_evaluator.evaluate(expression=condition_expression)
        condition = (condition != 0).astype(int)
    else:
        return None

    return np.array(condition)


def apply_condition(input_array: NDArray[np.float64], condition: NDArray[np.float64] | None) -> NDArray[np.float64]:
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
        return deepcopy(input_array)
    else:
        return np.where(condition, input_array, 0)


def get_power_loss_factor_from_expression(
    expression_evaluator: ExpressionEvaluator,
    power_loss_factor_expression: Expression,
) -> NDArray[np.float64] | None:
    """Evaluate power loss factor expression and compute resulting power loss factor vector.

    Args:
        expression_evaluator (ExpressionEvaluator): Service with all info to evaluate expressions.
        power_loss_factor_expression: The condition expression

    Returns:
        Assembled power loss factor vector
    """
    if power_loss_factor_expression is not None:
        power_loss_factor = expression_evaluator.evaluate(expression=power_loss_factor_expression)
    else:
        return None
    return np.array(power_loss_factor)


def apply_power_loss_factor(
    energy_usage: NDArray[np.float64], power_loss_factor: NDArray[np.float64] | None
) -> NDArray[np.float64]:
    """Apply resulting required power taking a (cable/motor...) power loss factor into account.

    Args:
        energy_usage: initial required energy usage [MW]
        power_loss_factor: Optional factor of the power (cable) loss.

    Returns:
        energy usage where power loss is accounted for, i.e. energy_usage/(1-power_loss_factor)
    """
    if power_loss_factor is None:
        return deepcopy(energy_usage)
    else:
        return energy_usage / (1.0 - power_loss_factor)
