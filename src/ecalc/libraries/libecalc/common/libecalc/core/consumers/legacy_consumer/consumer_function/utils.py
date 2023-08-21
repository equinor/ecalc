from copy import deepcopy
from typing import Optional

import numpy as np
from libecalc.core.consumers.legacy_consumer.consumer_function.results import (
    ConditionsAndPowerLossResult,
)
from libecalc.dto import VariablesMap
from libecalc.expression import Expression
from numpy.typing import NDArray


def calculate_energy_usage_with_conditions_and_power_loss(
    variables_map: VariablesMap,
    energy_usage: NDArray[np.float64],
    condition_expression: Expression,
    power_loss_factor_expression: Expression,
    power_usage: Optional[NDArray[np.float64]] = None,
) -> ConditionsAndPowerLossResult:
    condition = get_condition_from_expression(
        variables_map=variables_map,
        condition_expression=condition_expression,
    )
    energy_usage_after_condition_before_power_loss_factor = (
        energy_usage * condition if condition is not None else deepcopy(energy_usage)
    )
    power_usage_after_condition_before_power_loss_factor = (
        (power_usage * condition if condition is not None else deepcopy(power_usage))
        if power_usage is not None
        else None
    )

    # Apply power loss factor
    power_loss_factor = (
        power_loss_factor_expression.evaluate(
            variables=variables_map.variables, fill_length=len(variables_map.time_vector)
        )
        if power_loss_factor_expression is not None
        else None
    )
    # Set final energy usage to energy usage after conditioning and power loss factor
    resulting_energy_usage = apply_power_loss_factor(
        energy_usage=energy_usage_after_condition_before_power_loss_factor,
        power_loss_factor=power_loss_factor,
    )

    resulting_power_usage = (
        apply_power_loss_factor(
            energy_usage=power_usage_after_condition_before_power_loss_factor,
            power_loss_factor=power_loss_factor,
        )
        if power_usage_after_condition_before_power_loss_factor is not None
        else None
    )

    return ConditionsAndPowerLossResult(
        condition=condition,
        power_loss_factor=power_loss_factor,
        energy_usage_after_condition_before_power_loss_factor=energy_usage_after_condition_before_power_loss_factor,
        resulting_energy_usage=resulting_energy_usage,
        resulting_power_usage=resulting_power_usage,
    )


def get_condition_from_expression(
    variables_map: VariablesMap,
    condition_expression: Expression,
) -> Optional[NDArray[np.int_]]:
    """Evaluate condition expression and compute resulting condition vector.

    Args:
        variables_map: A map of all numeric arrays used in expressions
        condition_expression: The condition expression

    Returns:
        Assembled condition vector
    """
    if condition_expression is not None:
        condition = condition_expression.evaluate(
            variables=variables_map.variables, fill_length=len(variables_map.time_vector)
        )
        condition = (condition != 0).astype(int)
    else:
        return None

    return np.array(condition)


def apply_condition(input_array: NDArray[np.float64], condition: Optional[NDArray[np.float64]]) -> NDArray[np.float64]:
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
    variables_map: VariablesMap,
    power_loss_factor_expression: Expression,
) -> Optional[NDArray[np.float64]]:
    """Evaluate power loss factor expression and compute resulting power loss factor vector.

    Args:
        variables_map: A map of all numeric arrays used in expressions
        power_loss_factor_expression: The condition expression

    Returns:
        Assembled power loss factor vector
    """
    if power_loss_factor_expression is not None:
        power_loss_factor = power_loss_factor_expression.evaluate(
            variables=variables_map.variables, fill_length=len(variables_map.time_vector)
        )
    else:
        return None
    return np.array(power_loss_factor)


def apply_power_loss_factor(
    energy_usage: NDArray[np.float64], power_loss_factor: Optional[NDArray[np.float64]]
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
