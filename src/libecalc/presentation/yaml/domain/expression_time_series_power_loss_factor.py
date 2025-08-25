import numpy as np
from numpy.typing import NDArray

from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class ExpressionTimeSeriesPowerLossFactor(TimeSeriesPowerLossFactor):
    """
    Provides power loss factor values by evaluating a time series expression.
    """

    def __init__(self, time_series_expression: TimeSeriesExpression):
        self._time_series_expression = time_series_expression

    def get_values(self) -> list[float]:
        """
        Returns the power loss factor values as a list.
        """
        power_loss_factor = self._time_series_expression.get_evaluated_expressions()

        if not power_loss_factor:
            return [0.0] * len(self._time_series_expression.expression_evaluator.get_periods())
        return list(power_loss_factor)

    def apply(
        self,
        energy_usage: NDArray[np.float64],
    ) -> list[float]:
        """
        Adjusts the input energy usage to account for power losses.

        Retrieves the corresponding power loss factor for each time step, and returns the adjusted
        energy usage as a list, where each value is calculated as:
            adjusted = energy_usage / (1 - power_loss_factor)

        Args:
            energy_usage: array of initial energy usage values [MW].

        Returns:
            List of energy usage values adjusted for power loss.
        """

        power_loss_factor = np.asarray(self.get_values(), dtype=np.float64)

        if not np.any(power_loss_factor):
            return list(energy_usage)
        return list(energy_usage / (1.0 - power_loss_factor))
