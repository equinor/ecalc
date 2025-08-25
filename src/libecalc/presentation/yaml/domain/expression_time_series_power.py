import numpy as np

from libecalc.common.time_utils import Periods
from libecalc.common.utils.rates import Rates, RateType
from libecalc.domain.regularity import Regularity
from libecalc.domain.time_series_power import TimeSeriesPower
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class ExpressionTimeSeriesPower(TimeSeriesPower):
    """
    Provides power values by evaluating a time series expression.

    This class supports configurable rate types via the `consumption_rate_type` parameter.
    - If `consumption_rate_type` is set to calendar day (default), power values are converted to stream day values using the specified regularity.
    - If set to stream day, power values are used as-is.
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

    def get_stream_day_values(self) -> list[float | None]:
        """
        Returns the stream day power values as a list.

        The values are calculated by converting calendar day values to stream day values
        using the specified regularity, and then applying the given condition expression.
        """

        # if regularity is 0 for a calendar day value, set stream day value to 0 for that step
        power = self._time_series_expression.get_masked_values()
        power_array = np.asarray(power, dtype=np.float64)

        if self._consumption_rate_type == RateType.CALENDAR_DAY:
            power_array = Rates.to_stream_day(
                calendar_day_rates=power_array,
                regularity=self._regularity.values,
            )

        return power_array.tolist()

    def get_periods(self) -> Periods:
        """
        Returns the periods associated with the time series expression.

        This is used to align the flow rate values with the corresponding periods.
        """
        return self._time_series_expression.expression_evaluator.get_periods()
