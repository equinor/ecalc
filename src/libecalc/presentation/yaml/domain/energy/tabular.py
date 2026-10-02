from __future__ import annotations

import math

from libecalc.common.ddd.value_object import value_object
from libecalc.common.time_utils import Period
from libecalc.energy.energy_types import Energy
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.energy.models.tabular import TabularModel
from libecalc.presentation.yaml.domain.energy.demand import TimeSeriesDemand
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@value_object
class TabularDemand[E: Energy](TimeSeriesDemand[E]):
    name: str
    energy_type: type[E]
    model: TabularModel
    variables: dict[str, TimeSeriesExpression]

    def get_demand(self, period: Period) -> E:
        value = self.model.evaluate({name: expression.get_value(period) for name, expression in self.variables.items()})
        if not math.isfinite(value):
            raise InvalidEnergyNetworkInputError(
                f"'{self.name}': the input for period {period} is outside the range of the table "
                "or has an invalid variable value."
            )
        return self.energy_type(value=value)
