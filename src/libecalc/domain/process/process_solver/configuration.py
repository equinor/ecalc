from collections.abc import Sequence
from dataclasses import dataclass
from functools import total_ordering
from typing import NewType, TypeVar
from uuid import UUID

T_co = TypeVar("T_co", covariant=True)

# NOTE: We define this Id here for simplicity for now, since
# ConfigurationHandler and Configuration depends on it, to avoid
# circular dependency
ConfigurationHandlerId = NewType("ConfigurationHandlerId", UUID)


@dataclass(frozen=True)
class Configuration[T_co]:
    configuration_handler_id: ConfigurationHandlerId
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
    merged = {config.configuration_handler_id: config for config in first_configurations}
    merged.update({config.configuration_handler_id: config for config in second_configurations})
    return list(merged.values())
