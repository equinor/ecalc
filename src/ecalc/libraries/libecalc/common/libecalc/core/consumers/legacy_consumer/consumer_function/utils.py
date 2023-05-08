from copy import deepcopy
from typing import Optional

import numpy as np
from libecalc.core.consumers.legacy_consumer.consumer_function.results import (
    ConditionsAndPowerLossResult,
)
from libecalc.dto import VariablesMap
from libecalc.expression import Expression


def calculate_energy_usage_with_conditions_and_power_loss(
    variables_map: VariablesMap,
    energy_usage: np.ndarray,
    condition_expression: Expression,
    power_loss_factor_expression: Expression,
    power_usage: Optional[np.ndarray] = None,
) -> ConditionsAndPowerLossResult:
    condition = compute_condition(
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


def compute_condition(
    variables_map: VariablesMap,
    condition_expression: Expression,
) -> Optional[np.ndarray]:
    """Evaluate condition expression and compute resulting condition vector.

    :param variables_map: A map of all numeric arrays used in expressions
    :param condition_expression: The condition expression
    :return: assembled condition vector
    """
    if condition_expression is not None:
        condition = condition_expression.evaluate(
            variables=variables_map.variables, fill_length=len(variables_map.time_vector)
        )
        condition = (condition != 0).astype(int)
    else:
        condition = None

    return condition


def apply_power_loss_factor(energy_usage: np.ndarray, power_loss_factor: Optional[np.ndarray]) -> np.ndarray:
    """Apply resulting required power taking a (cable/motor...) power loss factor into account.

    :param energy_usage: initial required energy usage [MW]
    :param power_loss_factor: Optional factor of the power (cable) loss.
    :return: energy usage where power loss is accounted for, i.e. energy_usage/(1-power_loss_factor)
    """
    if power_loss_factor is None:
        return deepcopy(energy_usage)
    else:
        return energy_usage / (1.0 - power_loss_factor)
