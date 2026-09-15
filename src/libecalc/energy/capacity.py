from enum import StrEnum

from libecalc.energy.energy_types import Energy


class CapacityFailureStatus(StrEnum):
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"


class CapacityFailure:
    def __init__(
        self,
        status: CapacityFailureStatus,
        required_energy: Energy,
        capacity: Energy,
    ) -> None:
        self.status = status
        self.required_energy = required_energy
        self.capacity = capacity
