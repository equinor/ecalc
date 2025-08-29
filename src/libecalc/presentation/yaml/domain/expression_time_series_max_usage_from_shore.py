from libecalc.domain.time_series_max_usage_from_shore import TimeSeriesMaxUsageFromShore
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class ExpressionTimeSeriesMaxUsageFromShore(TimeSeriesMaxUsageFromShore):
    """
    Provides max usage from shore values by evaluating a time series expression.
    """

    def __init__(self, time_series_expression: TimeSeriesExpression):
        self._time_series_expression = time_series_expression

    def get_values(self) -> list[float]:
        """
        Returns the max usage from shore values.
        """

        max_usage_from_shore_values = self._time_series_expression.get_evaluated_expressions()

        return max_usage_from_shore_values
