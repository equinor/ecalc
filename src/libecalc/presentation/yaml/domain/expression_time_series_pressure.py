from collections.abc import Sequence

from libecalc.domain.time_series_pressure import TimeSeriesPressure
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class ExpressionTimeSeriesPressure(TimeSeriesPressure):
    """
    Provides pressure values by evaluating a time series expression.

    """

    def __init__(
        self,
        time_series_expression: TimeSeriesExpression,
    ):
        self._time_series_expression = time_series_expression

    def get_values(self) -> Sequence[float]:
        """
        Returns the pressure values as a NumPy array.

        """

        pressure_values = self._time_series_expression.get_evaluated_expressions()

        return pressure_values
