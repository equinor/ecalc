from collections.abc import Sequence

from libecalc.domain.time_series_fluid_density import TimeSeriesFluidDensity
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class ExpressionTimeSeriesFluidDensity(TimeSeriesFluidDensity):
    """
    Provides fluid density values by evaluating a time series expression.
    """

    def __init__(self, time_series_expression: TimeSeriesExpression):
        self._time_series_expression = time_series_expression

    def get_values(self) -> Sequence[float]:
        """
        Returns the fluid density values as a NumPy array.
        """

        fluid_density_values = self._time_series_expression.get_evaluated_expressions()

        return fluid_density_values
