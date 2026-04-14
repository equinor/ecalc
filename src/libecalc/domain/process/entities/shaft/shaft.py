import uuid
from abc import ABC, abstractmethod
from typing import NewType
from uuid import UUID

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.process_solver.boundary import Boundary

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
        self._compressors: list[Compressor] = []

    def get_id(self) -> ShaftId:
        return self._id

    @abstractmethod
    def set_speed(self, value: float) -> None:
        pass

    def connect(self, compressor: Compressor) -> None:
        if compressor in self._compressors:
            raise ProgrammingError("Compressor is already registered on this shaft.")
        self._compressors.append(compressor)

    def get_compressors(self) -> list[Compressor]:
        return list(self._compressors)

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
        from libecalc.domain.process.process_solver.boundary import Boundary

        if not self._compressors:
            raise ValueError("No compressors registered on this shaft.")
        min_speed = max(c.compressor_chart.minimum_speed for c in self._compressors)
        max_speed = min(c.compressor_chart.maximum_speed for c in self._compressors)
        return Boundary(min=min_speed, max=max_speed)

    def _apply_speed(self, value: float):
        self._speed_rpm = value
        for compressor in self._compressors:
            compressor.set_speed(value)


class SingleSpeedShaft(Shaft):
    def set_speed(self, value: float):
        if self._speed_rpm is None:
            self._apply_speed(value)
        elif value != self._speed_rpm:
            raise AttributeError("Speed has already been set. Cannot modify speed of SingleSpeedShaft")


class VariableSpeedShaft(Shaft):
    def set_speed(self, value: float):
        self._apply_speed(value)
