import uuid
from abc import ABC, abstractmethod
from typing import NewType
from uuid import UUID

class MechanicalComponent(ABC):

    @abstractmethod
    def get_id(self) -> UUID: ...

ShaftId = NewType("ShaftId", UUID)

def create_shaft_id() -> ShaftId:
    return ShaftId(uuid.uuid4())

class Shaft(MechanicalComponent, ABC):
    """Abstract base class for a shaft.

    Can be expanded to include more properties and methods as needed.
    Name, id, units connected to it, etc

    TODO: Instead of "that a compressor has a shaft", should we flip it and say that a shaft has compressors? Or the unit it is attached to?
    ie, the shaft needs to know when a solver or algorithm changes it, and it needs to make sure that all connected units are updated w. same speed ...
    should we then also have a "mechanical system", that is related to the shaft, motor, gear box etc? and also the compressor - but from a mechanical perspective
    """

    def __init__(self, speed_rpm: float | None = None):
        self._speed_rpm = speed_rpm
        self._id = create_shaft_id()
        # TODO: The speed should not be set when creating a shaft, it is a part of the config/state of the process system,
        #  and can be changed by the solver/algorithm. We can have a "config" or "state" object that is passed to the shaft,
        #  and the shaft can update it when the speed is changed. TOTHINK: Would shared state where solver can change, and system must read
        # from state be a better solution - ie inspired by react state management?

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
