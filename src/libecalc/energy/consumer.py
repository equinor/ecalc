from __future__ import annotations

import abc

from libecalc.energy.energy_failure import EnergyFailure, capacity_failures
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId


class Consumer(EnergyUnit, abc.ABC):
    """Terminal energy unit representing an energy demand."""

    def __init__(
        self,
        name: str,
        output_energy: Energy,
        capacity: Energy | None = None,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name, energy_unit_id)
        self._output_energy = output_energy
        self._capacity = capacity

    def get_output_energy(self) -> Energy:
        return self._output_energy

    def get_capacity(self) -> Energy | None:
        return self._capacity

    def get_failures(self) -> list[EnergyFailure]:
        return capacity_failures(self._output_energy, self._capacity)

    @classmethod
    @abc.abstractmethod
    def get_input_energy_type(cls) -> type[Energy]: ...

    @classmethod
    def get_output_energy_type(cls) -> None:
        return None
