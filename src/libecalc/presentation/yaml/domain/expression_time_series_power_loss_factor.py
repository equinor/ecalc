from collections.abc import Sequence

import numpy as np

from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class ExpressionTimeSeriesPowerLossFactor:
    """
    Provides power loss factor values by evaluating a time series expression.
    """

    def __init__(self, time_series_expression: TimeSeriesExpression):
        self._time_series_expression = time_series_expression

    def get_values(self) -> Sequence[float] | None:
        """
        Returns the power loss factor values as a list.
        """
        power_loss_factor = self._time_series_expression.get_evaluated_expressions()

        if not power_loss_factor:  # Empty list
            return None

        return power_loss_factor

    def apply(
        self,
        energy_usage: Sequence[float] | np.ndarray,
    ) -> np.ndarray:
        """
        Apply resulting required power taking a (cable/motor...) power loss factor into account.
        Args:
            energy_usage: initial required energy usage [MW]
        Returns:
            energy usage where power loss is accounted for, i.e. energy_usage/(1-power_loss_factor)
        """
        power_loss_factor = self.get_values()
        energy_usage_arr = np.asarray(energy_usage, dtype=np.float64)

        if power_loss_factor is None:
            result = energy_usage_arr
        else:
            power_loss_factor_arr = np.asarray(power_loss_factor, dtype=np.float64)
            result = energy_usage_arr / (1.0 - power_loss_factor_arr)
        return result
