from __future__ import annotations

import abc

from libecalc.common.ddd.value_object import value_object
from libecalc.common.time_utils import Period
from libecalc.energy import Energy
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TimeSeriesDemand[E: Energy](abc.ABC):
    energy_type: type[E]

    @abc.abstractmethod
    def get_demand(self, period: Period) -> E | None: ...


@value_object
class ExpressionDemand[E: Energy](TimeSeriesDemand[E]):
    energy_type: type[E]
    expression: TimeSeriesExpression | None

    def get_demand(self, period: Period) -> E | None:
        if self.expression is None:
            return None
        return self.energy_type(value=self.expression.get_value(period))
