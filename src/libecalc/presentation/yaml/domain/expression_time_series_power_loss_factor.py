import numpy as np

from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class ExpressionTimeSeriesPowerLossFactor(TimeSeriesPowerLossFactor):
    """
    Provides power loss factor values by evaluating a time series expression.
    """

    def __init__(self, time_series_expression: TimeSeriesExpression):
        self._time_series_expression = time_series_expression

    def get_values(self, length=None) -> list[float]:
        """
        Returns the power loss factor values as a list.
        """
        power_loss_factor = self._time_series_expression.get_evaluated_expressions()

        if not power_loss_factor:
            if length is not None:
                return [0.0] * length
            return []
        return list(power_loss_factor)

    def apply(
        self,
        energy_usage: list[float | None] | np.ndarray,
    ) -> list[float]:
        """
        Adjusts the input energy usage to account for power losses.

        Converts the input sequence to a NumPy array, replaces missing values (None or NaN) with 0.0,
        retrieves the corresponding power loss factor for each time step, and returns the adjusted
        energy usage as a list, where each value is calculated as:
            adjusted = energy_usage / (1 - power_loss_factor)

        Args:
            energy_usage: Sequence or array of initial energy usage values [MW], may contain None.

        Returns:
            List of energy usage values adjusted for power loss.
        """

        energy_usage_arr = np.asarray(energy_usage, dtype=np.float64)
        # Replace nan (from None) with 0.0 or another default value
        energy_usage_arr = np.nan_to_num(energy_usage_arr, nan=0.0)

        power_loss_factor = self.get_values(length=len(energy_usage_arr))

        power_loss_factor_arr = np.asarray(power_loss_factor, dtype=np.float64)
        if not np.any(power_loss_factor_arr):
            return list(energy_usage_arr)
        return list(energy_usage_arr / (1.0 - power_loss_factor_arr))
