from __future__ import annotations

from libecalc.common.time_utils import Period
from libecalc.energy import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnit
from libecalc.presentation.yaml.domain.energy.demand import TimeSeriesDemand


class TimeSeriesConsumer(TimeSeriesEnergyUnit):
    def __init__(
        self,
        *,
        name: str,
        demand: TimeSeriesDemand[Energy],
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.demand = demand

    def get_demand(self, period: Period) -> Energy | None:
        return self.demand.get_demand(period)

    def get_input_energy_type(self) -> type[Energy]:
        return self.demand.energy_type
