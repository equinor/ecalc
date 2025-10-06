import numpy as np

from libecalc.common.time_utils import Periods
from libecalc.common.utils.rates import Rates
from libecalc.domain.time_series_regularity import TimeSeriesRegularity
from libecalc.domain.time_series_variable import TimeSeriesVariable
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class ExpressionTimeSeriesVariable(TimeSeriesVariable):
    """
    Wraps a time series expression for use as a variable in tabular consumer functions.
    Handles rate conversion and conditional masking.
    """

    def __init__(
        self,
        name: str,
        time_series_expression: TimeSeriesExpression,
        regularities: TimeSeriesRegularity,
        is_rate: bool = True,
    ):
        self._name = name
        self._time_series_expression = time_series_expression
        self._regularities = regularities
        self._is_rate = is_rate

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_rate(self) -> bool:
        return self._is_rate

    def get_values(self) -> list[float]:
        values: np.ndarray = np.asarray(self._time_series_expression.get_masked_values(), dtype=np.float64)
        # If some of these are rates, we need to calculate stream day rate for use
        # Also take a copy of the calendar day rate and stream day rate for input to result object

        if self.is_rate:
            values = Rates.to_stream_day(
                calendar_day_rates=values,
                regularities=self._regularities.values,
            )

        return values.tolist()

    def get_periods(self) -> Periods:
        """
        Returns the periods associated with the time series expression.

        """
        return self._time_series_expression.expression_evaluator.get_periods()
