from dataclasses import dataclass
from functools import total_ordering
from typing import Generic, TypeVar

from libecalc.domain.process.entities.shaft.shaft import ShaftId
from libecalc.domain.process.process_system.process_system import ProcessSystemId
from libecalc.domain.process.process_system.process_unit import ProcessUnitId

T_co = TypeVar("T_co", covariant=True)

SimulationUnitId = ProcessUnitId | ProcessSystemId | ShaftId


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
