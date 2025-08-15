import numpy as np

from libecalc.common.time_utils import Period, Periods
from libecalc.common.utils.rates import Rates
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.utils import (
    apply_condition,
    get_condition_from_expression,
)
from libecalc.domain.regularity import Regularity
from libecalc.domain.time_series_variable import TimeSeriesVariable
from libecalc.expression import Expression
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
        regularity: Regularity,
        is_rate: bool = True,
        condition_expression: Expression | dict[Period, Expression] | None = None,
    ):
        self._name = name
        self._time_series_expression = time_series_expression
        self._regularity = regularity
        self._is_rate = is_rate
        self.condition = get_condition_from_expression(
            expression_evaluator=self._time_series_expression.expression_evaluator,
            condition_expression=condition_expression,
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_rate(self) -> bool:
        return self._is_rate

    def get_values(self) -> list[float]:
        values: np.ndarray = np.asarray(self._time_series_expression.get_evaluated_expressions(), dtype=np.float64)
        # If some of these are rates, we need to calculate stream day rate for use
        # Also take a copy of the calendar day rate and stream day rate for input to result object

        if self.is_rate:
            values = Rates.to_stream_day(
                calendar_day_rates=values,
                regularity=self._regularity.values,
            )

        values = apply_condition(
            input_array=values,
            condition=self.condition,
        )
        return values.tolist()

    def get_periods(self) -> Periods:
        """
        Returns the periods associated with the time series expression.

        """
        return self._time_series_expression.expression_evaluator.get_periods()
