import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from functools import total_ordering
from typing import Generic, NewType, TypeVar
from uuid import UUID

T_co = TypeVar("T_co", covariant=True)

SimulationUnitId = NewType("SimulationUnitId", UUID)


def create_simulation_unit_id() -> SimulationUnitId:
    return SimulationUnitId(uuid.uuid4())


@dataclass(frozen=True)
class Configuration(Generic[T_co]):
    simulation_unit_id: SimulationUnitId
    value: T_co


@total_ordering
@dataclass
class SpeedConfiguration:
    speed: float

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SpeedConfiguration):
            return NotImplemented
        return self.speed == other.speed

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SpeedConfiguration):
            return NotImplemented
        return self.speed < other.speed


@dataclass
class ChokeConfiguration:
    delta_pressure: float


@dataclass
class RecirculationConfiguration:
    recirculation_rate: float

    def __post_init__(self):
        self.recirculation_rate = float(self.recirculation_rate)


OperatingConfiguration = SpeedConfiguration | ChokeConfiguration | RecirculationConfiguration


def merge_configurations(
    first_configurations: Sequence[Configuration[OperatingConfiguration]],
    second_configurations: Sequence[Configuration[OperatingConfiguration]],
) -> Sequence[Configuration[OperatingConfiguration]]:
    """Merge two sequences; entries in second_configurations take precedence by simulation_unit_id."""
    merged = {config.simulation_unit_id: config for config in first_configurations}
    merged.update({config.simulation_unit_id: config for config in second_configurations})
    return list(merged.values())
