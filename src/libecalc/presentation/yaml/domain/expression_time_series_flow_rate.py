from collections.abc import Sequence

import numpy as np

from libecalc.common.time_utils import Period
from libecalc.common.utils.rates import Rates
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

    This class assumes that the input time series expression yields flow rates per calendar day.
    - Stream day values are derived by converting calendar day rates using the specified regularity,
      and then applying an optional condition expression to filter or modify the results.

    """

    def __init__(
        self,
        time_series_expression: TimeSeriesExpression,
        regularity: Regularity,
        condition_expression: Expression | dict[Period, Expression] | None = None,
    ):
        self._time_series_expression = time_series_expression
        self._regularity = regularity
        self.condition = get_condition_from_expression(
            expression_evaluator=self._time_series_expression.expression_evaluator,
            condition_expression=condition_expression,
        )

    def get_stream_day_values(self) -> Sequence[float]:
        """
        Returns the stream day flow rate values as a NumPy array.

        The values are calculated by converting calendar day rates to stream day rates
        using the specified regularity, and then applying the given condition expression.
        """

        # if regularity is 0 for a calendar day rate, set stream day rate to 0 for that step
        calendar_day_rate = self._time_series_expression.get_evaluated_expressions()
        stream_day_rate = apply_condition(
            input_array=Rates.to_stream_day(
                calendar_day_rates=np.asarray(calendar_day_rate, dtype=np.float64),
                regularity=self._regularity.get_values,
            ),
            condition=self.condition,
        )
        return stream_day_rate
