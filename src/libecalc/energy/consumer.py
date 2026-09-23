from __future__ import annotations

import abc

from libecalc.energy.energy_failure import EnergyFailure
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId


class Consumer(EnergyUnit, abc.ABC):
    """Terminal energy unit representing an energy demand."""

    def __init__(
        self,
        name: str,
        demand: Energy,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name, energy_unit_id)
        self._demand = demand

    def get_demand(self) -> Energy:
        return self._demand

    def get_failures(self) -> list[EnergyFailure]:
        return []

    @classmethod
    @abc.abstractmethod
    def get_input_energy_type(cls) -> type[Energy]: ...

    @classmethod
    def get_output_energy_type(cls) -> None:
        return None
