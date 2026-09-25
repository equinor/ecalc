from __future__ import annotations

from dataclasses import dataclass

from libecalc.common.time_utils import Period
from libecalc.energy import Energy
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnit
from libecalc.presentation.yaml.domain.energy.demand import TimeSeriesDemand


@dataclass(kw_only=True)
class TimeSeriesConsumer(TimeSeriesEnergyUnit):
    demand: TimeSeriesDemand[Energy]

    def get_demand(self, period: Period) -> Energy | None:
        return self.demand.get_demand(period)

    def get_input_energy_type(self) -> type[Energy]:
        return self.demand.energy_type
