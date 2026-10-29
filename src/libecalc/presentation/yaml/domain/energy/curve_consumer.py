from __future__ import annotations

import math

from libecalc.common.ddd.value_object import value_object
from libecalc.common.time_utils import Period
from libecalc.energy.energy_types import Energy
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.energy.models.curve_interpolator import CurveInterpolator
from libecalc.presentation.yaml.domain.energy.demand import TimeSeriesDemand
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@value_object
class CurveConsumerDemand[E: Energy](TimeSeriesDemand[E]):
    energy_type: type[E]
    model: CurveInterpolator
    variable: TimeSeriesExpression

    def get_demand(self, period: Period) -> E:
        value = self.model.energy_for_variable(self.variable.get_value(period))
        if math.isnan(value):
            raise InvalidEnergyNetworkInputError(
                f"Curve consumer input for period {period} is outside the model's sampled range."
            )
        return self.energy_type(value=value)
