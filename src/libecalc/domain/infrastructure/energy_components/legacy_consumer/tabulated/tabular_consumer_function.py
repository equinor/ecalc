import numpy as np

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated.tabular_energy_function import (
    TabularEnergyFunction,
)
from libecalc.domain.process.core.results import EnergyFunctionResult
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor
from libecalc.domain.time_series_variable import TimeSeriesVariable


class TabularConsumerFunction(ConsumerFunction):
    """
    Consumer function based on tabulated energy usage data.

    This class evaluates energy usage (power or fuel) for a consumer by:
      - Evaluating time series variables (with condition and rate conversion applied).
      - Interpolating tabular data using these variable values via `TabularEnergyFunction`.
      - Optionally applying a power loss factor.

    The result is energy usage in [MW] (electricity) or [Sm3/day] (fuel).
    For electricity, power is also included in the result.

    Args:
        headers (list[str]): Column headers for the tabular data.
        data (list[list[float]]): Tabular data, one list per header.
        energy_usage_adjustment_constant (float): Constant to adjust energy usage.
        energy_usage_adjustment_factor (float): Factor to adjust energy usage.
        variables (list[TimeSeriesVariable]): Variables to evaluate and use for interpolation.
        power_loss_factor (TimeSeriesPowerLossFactor | None): Optional power loss factor.
    """

    def __init__(
        self,
        headers: list[str],
        data: list[list[float]],
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        variables: list[TimeSeriesVariable],
        power_loss_factor: TimeSeriesPowerLossFactor | None = None,
    ):
        """Tabulated consumer function [MW] (energy) or [Sm3/day] (fuel)."""
        # Consistency of variables between tabulated_energy_function and variables_expressions must be validated up
        # front
        self._tabular_energy_function = TabularEnergyFunction(
            headers=headers,
            data=data,
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
        )
        self._variables = variables

        # Typically used for power line loss subsea et.c.
        self._power_loss_factor = power_loss_factor

    def evaluate(self) -> ConsumerFunctionResult:
        """
        Evaluates the consumer function for the given input data.

        Steps:
            1. Evaluates all variables (with condition and rate conversion).
            2. Interpolates the tabular energy function using these values.
            3. Optionally applies a power loss factor.
            4. Returns a result object with energy usage, validity, and related data.

        Args:
            expression_evaluator (ExpressionEvaluator): Evaluator for variable and condition expressions.
            regularity (list[float]): Regularity values for rate conversion.

        Returns:
            ConsumerFunctionResult: Result containing energy usage, validity, and related data.
        """

        energy_function_result = self.evaluate_variables(
            variables=self._variables,
        )

        # Apply power loss factor if present
        if self._power_loss_factor is not None:
            energy_usage = self._power_loss_factor.apply(
                energy_usage=np.asarray(energy_function_result.energy_usage, dtype=np.float64)
            )
            power_loss_factor = self._power_loss_factor.get_values()
        else:
            energy_usage = energy_function_result.energy_usage
            power_loss_factor = None

        return ConsumerFunctionResult(
            periods=self._variables[0].get_periods(),
            is_valid=np.asarray(energy_function_result.is_valid),
            energy_function_result=energy_function_result,
            energy_usage_before_power_loss_factor=np.asarray(energy_function_result.energy_usage, dtype=np.float64),
            power_loss_factor=np.asarray(power_loss_factor, dtype=np.float64),
            energy_usage=np.asarray(energy_usage, dtype=np.float64),
        )

    def evaluate_variables(self, variables: list[TimeSeriesVariable]) -> EnergyFunctionResult:
        """
        Interpolates energy usage for the provided variables.

        Args:
            variables (list[TimeSeriesVariable]): List of variables to evaluate and use for interpolation.

        Returns:
            EnergyFunctionResult: Result containing energy usage, units, and power (if applicable).
        """

        variables_map_by_name = {variable.name: variable.get_values() for variable in variables}
        _check_variables_match_required(
            variables_to_evaluate=list(variables_map_by_name.keys()),
            required_variables=self._tabular_energy_function.required_variables,
        )
        variables_array_for_evaluation = np.asarray(
            [
                variables_map_by_name.get(variable_name)
                for variable_name in self._tabular_energy_function.required_variables
            ]
        )
        variables_array_for_evaluation = np.squeeze(variables_array_for_evaluation)  # Remove empty dimensions
        variables_array_for_evaluation = np.transpose(variables_array_for_evaluation)
        energy_usage = self._tabular_energy_function.interpolate(variables_array_for_evaluation)

        energy_usage_list = array_to_list(energy_usage)
        if energy_usage_list is None:
            energy_usage_list = []  # Provide empty list as fallback

        return EnergyFunctionResult(
            energy_usage=energy_usage_list,
            energy_usage_unit=Unit.MEGA_WATT
            if self._tabular_energy_function.energy_usage_type == EnergyUsageType.POWER
            else Unit.STANDARD_CUBIC_METER_PER_DAY,
            power=energy_usage_list
            if self._tabular_energy_function.energy_usage_type == EnergyUsageType.POWER
            else None,
            power_unit=Unit.MEGA_WATT
            if self._tabular_energy_function.energy_usage_type == EnergyUsageType.POWER
            else None,
        )


def _check_variables_match_required(variables_to_evaluate: list[str], required_variables: list[str]):
    if set(variables_to_evaluate) != set(required_variables):
        msg = (
            "Variables to evaluate must correspond to required variables. You should not end up"
            " here, please contact support."
        )
        logger.exception(msg)
        raise IllegalStateException(msg)
