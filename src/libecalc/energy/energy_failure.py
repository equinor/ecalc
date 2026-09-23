from enum import StrEnum

from libecalc.common.ddd import value_object
from libecalc.energy.energy_types import Energy


class EnergyFailureStatus(StrEnum):
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"


@value_object
class EnergyFailure:
    status: EnergyFailureStatus


@value_object
class CapacityFailure(EnergyFailure):
    required_energy: Energy
    capacity: Energy


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
