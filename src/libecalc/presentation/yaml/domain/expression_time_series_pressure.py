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

    def get_values(self) -> list[float]:
        """
        Returns the pressure values as a list.

        """

        pressure_values = self._time_series_expression.get_evaluated_expressions()

        return list(pressure_values)
