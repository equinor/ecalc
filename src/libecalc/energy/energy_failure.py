from enum import StrEnum

from libecalc.energy.energy_types import Energy


class EnergyFailureStatus(StrEnum):
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"


class EnergyFailure:
    def __init__(self, status: EnergyFailureStatus) -> None:
        self.status = status


class CapacityFailure(EnergyFailure):
    def __init__(
        self,
        status: EnergyFailureStatus,
        required_energy: Energy,
        capacity: Energy,
    ) -> None:
        super().__init__(status=status)
        self.required_energy = required_energy
        self.capacity = capacity


def capacity_failures(required_energy: Energy, capacity: Energy | None) -> list[EnergyFailure]:
    """Report a capacity failure when a unit must deliver more than its rating.

    Energy is never capped, so exceeding capacity is reported rather than enforced. A unit without a
    capacity is unlimited and never fails. Shared by every unit that carries a capacity.
    """
    if capacity is not None and required_energy > capacity:
        return [
            CapacityFailure(
                status=EnergyFailureStatus.CAPACITY_EXCEEDED,
                required_energy=required_energy,
                capacity=capacity,
            )
        ]
    return []
