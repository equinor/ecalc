import uuid
from abc import ABC, abstractmethod
from typing import Final, Generic, NewType, Protocol, TypeVar, runtime_checkable
from uuid import UUID

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.configuration import (
    Configuration,
    SpeedConfiguration,
)
from libecalc.domain.process.process_solver.configuration_handler import ConfigurationHandler, ConfigurationHandlerId

ShaftId = NewType("ShaftId", UUID)


def create_shaft_id() -> ShaftId:
    return ShaftId(uuid.uuid4())


@runtime_checkable
class ShaftConnectable(Protocol):
    """Any unit that can be mounted on a shaft: exposes speed bounds and accepts speed updates."""

    @property
    def minimum_speed(self) -> float: ...

    @property
    def maximum_speed(self) -> float: ...

    def set_speed(self, speed: float) -> None: ...


_T = TypeVar("_T", bound=ShaftConnectable)


class Shaft(ConfigurationHandler, ABC, Generic[_T]):
    """Abstract base class for a shaft driving a homogeneous set of process units.

    A shaft connects to either compressors or pumps — never a mix of both.
    The generic parameter _T enforces this at the type-checking level:
        VariableSpeedShaft[Compressor], SingleSpeedShaft[Pump], etc.
    """

    def __init__(
        self,
        configuration_handler_id: ConfigurationHandlerId | None = None,
        speed_rpm: float | None = None,
    ):
        self._id: Final[ConfigurationHandlerId] = configuration_handler_id or ConfigurationHandler._create_id()
        self._speed_rpm = speed_rpm
        self._units: list[_T] = []

    def get_id(self) -> ConfigurationHandlerId:
        return self._id

    def handle_configuration(self, configuration: Configuration):
        assert configuration.configuration_handler_id == self._id, (
            f"Configuration id '{configuration.configuration_handler_id}' does not match shaft id '{self._id}'"
        )
        assert isinstance(configuration.value, SpeedConfiguration), (
            f"Expected configuration value to be of type 'SpeedConfiguration' for shaft speed, got '{type(configuration.value)}'"
        )
        self.set_speed(configuration.value.speed)

    @abstractmethod
    def set_speed(self, value: float) -> None:
        pass

    def connect(self, unit: _T) -> None:
        if unit in self._units:
            raise ProgrammingError("Unit is already registered on this shaft.")
        self._units.append(unit)

    def get_speed(self) -> float:
        if self._speed_rpm is None:
            return float("nan")
        return self._speed_rpm

    def reset_speed(self):
        self._speed_rpm = None

    @property
    def speed_is_defined(self) -> bool:
        return self._speed_rpm is not None

    def get_speed_boundary(self) -> Boundary:
        if not self._units:
            raise ValueError("No units registered on this shaft.")
        min_speed = max(u.minimum_speed for u in self._units)
        max_speed = min(u.maximum_speed for u in self._units)
        return Boundary(min=min_speed, max=max_speed)

    def _apply_speed(self, value: float):
        self._speed_rpm = value
        for unit in self._units:
            unit.set_speed(value)


class SingleSpeedShaft(Shaft[_T]):
    def set_speed(self, value: float):
        if self._speed_rpm is None:
            self._apply_speed(value)
        elif value != self._speed_rpm:
            raise AttributeError("Speed has already been set. Cannot modify speed of SingleSpeedShaft")


class VariableSpeedShaft(Shaft[_T]):
    def set_speed(self, value: float):
        self._apply_speed(value)
