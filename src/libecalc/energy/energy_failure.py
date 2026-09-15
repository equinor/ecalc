from enum import StrEnum

from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId


class EnergyFailureStatus(StrEnum):
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"


class EnergyFailure:
    def __init__(self, status: EnergyFailureStatus) -> None:
        self.status = status


class CapacityFailure(EnergyFailure):
    def __init__(
        self,
        status: EnergyFailureStatus,
        energy_unit_id: EnergyUnitId,
        required_energy: Energy,
        capacity: Energy,
    ) -> None:
        super().__init__(status=status)
        self.energy_unit_id = energy_unit_id
        self.required_energy = required_energy
        self.capacity = capacity
