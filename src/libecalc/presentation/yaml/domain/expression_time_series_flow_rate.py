import numpy as np

from libecalc.common.time_utils import Periods
from libecalc.common.utils.rates import Rates, RateType
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.regularity import Regularity
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class InvalidFlowRateException(DomainValidationException):
    """Exception raised for invalid flow rate values."""

    def __init__(self, rate: float, rate_expression: str):
        if str(rate) == rate_expression:
            msg = f"All rate values must be non negative, got {rate}."
        else:
            msg = f"All rate values must be non negative, got {rate} in {rate_expression}."
        super().__init__(message=msg)


class ExpressionTimeSeriesFlowRate(TimeSeriesFlowRate):
    """
    Provides flow rate values by evaluating a time series expression.

    This class supports configurable rate types via the `consumption_rate_type` parameter.
    - If `consumption_rate_type` is set to calendar day (default), flow rates are converted to stream day rates using the specified regularity.
    - If set to stream day, rates are used as-is.
    - An optional condition expression can be applied to filter or modify the results.
    """

    def __init__(
        self,
        time_series_expression: TimeSeriesExpression,
        regularity: Regularity,
        consumption_rate_type: RateType | None = RateType.CALENDAR_DAY,
    ):
        self._time_series_expression = time_series_expression
        self._regularity = regularity
        assert isinstance(consumption_rate_type, RateType)
        self._consumption_rate_type = consumption_rate_type
        self._rate_values = self._get_stream_day_values()
        if self._rate_values is not None:
            self._validate()

    def _validate(self):
        """Validate that all flow rate values are positive."""
        for rate in self._rate_values:
            assert rate is not None
            if rate < 0:
                raise InvalidFlowRateException(rate, str(self._time_series_expression.get_expression()))

    def _get_stream_day_values(self) -> list[float]:
        """
        Returns the stream day flow rate values.

        The values are calculated by converting calendar day rates to stream day rates
        using the specified regularity, and then applying the given condition expression.
        """

        # if regularity is 0 for a calendar day rate, set stream day rate to 0 for that step
        rate = self._time_series_expression.get_masked_values()
        rate_array = np.asarray(rate, dtype=np.float64)

        if self._consumption_rate_type == RateType.CALENDAR_DAY:
            rate_array = Rates.to_stream_day(
                calendar_day_rates=rate_array,
                regularity=self._regularity.values,
            )

        return rate_array.tolist()

    def get_stream_day_values(self) -> list[float]:
        """
        Returns the flow rate values as a list in stream day units.

        """
        return self._rate_values

    def get_periods(self) -> Periods:
        """
        Returns the periods associated with the time series expression.

        This is used to align the flow rate values with the corresponding periods.
        """
        return self._time_series_expression.expression_evaluator.get_periods()
