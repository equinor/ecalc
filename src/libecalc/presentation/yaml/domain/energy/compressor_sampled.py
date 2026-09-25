from __future__ import annotations

from libecalc.common.ddd.value_object import value_object
from libecalc.common.time_utils import Period
from libecalc.energy.energy_types import Energy
from libecalc.energy.models.sampled_compressor import SampledCompressor
from libecalc.presentation.yaml.domain.energy.demand import TimeSeriesDemand
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


def _value_at(expression: TimeSeriesExpression | None, period: Period) -> float | None:
    return expression.get_value(period) if expression is not None else None


@value_object
class CompressorSampledDemand[E: Energy](TimeSeriesDemand[E]):
    energy_type: type[E]
    model: SampledCompressor
    rate: TimeSeriesExpression | None = None
    suction_pressure: TimeSeriesExpression | None = None
    discharge_pressure: TimeSeriesExpression | None = None

    def get_demand(self, period: Period) -> E | None:
        result = self.model.evaluate(
            rate=_value_at(self.rate, period),
            suction_pressure=_value_at(self.suction_pressure, period),
            discharge_pressure=_value_at(self.discharge_pressure, period),
        )
        if self.model.get_fuel_power_curve() is not None:
            assert result.power is not None
            return self.energy_type(value=result.power)
        return self.energy_type(value=result.energy_usage)
