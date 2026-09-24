from __future__ import annotations

from libecalc.energy.energy_failure import EnergyFailure, capacity_failures
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId


class Consumer(EnergyUnit):
    def __init__(
        self,
        name: str,
        demand: Energy,
        capacity: Energy | None = None,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name, energy_unit_id)
        self._demand = demand
        self._capacity = capacity

    def get_demand(self) -> Energy:
        return self._demand

    def get_capacity(self) -> Energy | None:
        return self._capacity

    def get_failures(self) -> list[EnergyFailure]:
        return capacity_failures(self._demand, self._capacity)

    def get_input_energy_type(self) -> type[Energy]:
        return type(self._demand)

    def get_output_energy_type(self) -> None:
        return None
