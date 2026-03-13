import uuid
from abc import ABC, abstractmethod
from typing import NewType
from uuid import UUID

ShaftId = NewType("ShaftId", UUID)


def create_shaft_id() -> ShaftId:
    return ShaftId(uuid.uuid4())


class Shaft(ABC):
    """Abstract base class for a shaft.

    Can be expanded to include more properties and methods as needed.
    Name, id, units connected to it, etc
    """

    def __init__(self, speed_rpm: float | None = None):
        self._id = create_shaft_id()
        self._speed_rpm = speed_rpm

    def get_id(self) -> ShaftId:
        return self._id

    @abstractmethod
    def set_speed(self, value: float) -> None:
        pass

    def get_speed(self) -> float:
        if self._speed_rpm is None:
            return float("nan")
        return self._speed_rpm

    def reset_speed(self):
        self._speed_rpm = None

    @property
    def speed_is_defined(self) -> bool:
        return self._speed_rpm is not None


class SingleSpeedShaft(Shaft):
    def set_speed(self, value: float):
        if self._speed_rpm is None:
            self._speed_rpm = value
        elif value != self._speed_rpm:
            raise AttributeError("Speed has already been set. Cannot modify speed of SingleSpeedShaft")


class VariableSpeedShaft(Shaft):
    def set_speed(self, value: float):
        self._speed_rpm = value
