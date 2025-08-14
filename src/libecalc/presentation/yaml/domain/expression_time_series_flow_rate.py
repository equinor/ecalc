import numpy as np

from libecalc.common.time_utils import Period, Periods
from libecalc.common.utils.rates import Rates, RateType
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.utils import (
    apply_condition,
    get_condition_from_expression,
)
from libecalc.domain.regularity import Regularity
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


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
        condition_expression: Expression | dict[Period, Expression] | None = None,
        consumption_rate_type: RateType | None = RateType.CALENDAR_DAY,
    ):
        self._time_series_expression = time_series_expression
        self._regularity = regularity
        assert isinstance(consumption_rate_type, RateType)
        self._consumption_rate_type = consumption_rate_type
        self.condition = get_condition_from_expression(
            expression_evaluator=self._time_series_expression.expression_evaluator,
            condition_expression=condition_expression,
        )

    def get_stream_day_values(self) -> list[float | None]:
        """
        Returns the stream day flow rate values.

        The values are calculated by converting calendar day rates to stream day rates
        using the specified regularity, and then applying the given condition expression.
        """

        # if regularity is 0 for a calendar day rate, set stream day rate to 0 for that step
        rate = self._time_series_expression.get_evaluated_expressions()
        rate_array = np.asarray(rate, dtype=np.float64)

        if self._consumption_rate_type == RateType.CALENDAR_DAY:
            rate_array = Rates.to_stream_day(
                calendar_day_rates=rate_array,
                regularity=self._regularity.values,
            )

        # If already stream_day, no conversion needed
        stream_day_rate = apply_condition(
            input_array=rate_array,
            condition=self.condition,
        )

        return stream_day_rate.tolist()

    def get_periods(self) -> Periods:
        """
        Returns the periods associated with the time series expression.

        This is used to align the flow rate values with the corresponding periods.
        """
        return self._time_series_expression.expression_evaluator.get_periods()
