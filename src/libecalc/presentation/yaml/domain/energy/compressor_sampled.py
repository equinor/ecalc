from __future__ import annotations

import enum
import math

from libecalc.common.ddd.value_object import value_object
from libecalc.common.time_utils import Period
from libecalc.energy.energy_types import Energy
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.energy.models.sampled_compressor import SampledCompressor
from libecalc.presentation.yaml.domain.energy.demand import TimeSeriesDemand
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class DemandSource(enum.Enum):
    ENERGY_USAGE = "energy_usage"
    POWER = "power"


def _value_at(expression: TimeSeriesExpression | None, period: Period) -> float | None:
    return expression.get_value(period) if expression is not None else None


@value_object
class CompressorSampledDemand[E: Energy](TimeSeriesDemand[E]):
    energy_type: type[E]
    model: SampledCompressor
    demand_source: DemandSource
    rate: TimeSeriesExpression | None = None
    suction_pressure: TimeSeriesExpression | None = None
    discharge_pressure: TimeSeriesExpression | None = None

    def get_demand(self, period: Period) -> E | None:
        result = self.model.evaluate(
            rate=_value_at(self.rate, period),
            suction_pressure=_value_at(self.suction_pressure, period),
            discharge_pressure=_value_at(self.discharge_pressure, period),
        )
        if self.demand_source is DemandSource.POWER:
            assert result.power is not None
            value = result.power
        else:
            value = result.energy_usage
        if math.isnan(value):
            raise InvalidEnergyNetworkInputError(
                f"Sampled compressor input for period {period} is outside the model's sampled range."
            )
        return self.energy_type(value=value)
