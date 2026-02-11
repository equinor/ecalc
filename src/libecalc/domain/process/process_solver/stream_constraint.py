import abc
from typing import TypeGuard

from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class StreamConstraint(abc.ABC):
    @abc.abstractmethod
    def check(self, stream: FluidStream | None) -> TypeGuard[FluidStream]: ...


class PressureStreamConstraint(StreamConstraint):
    def __init__(self, target_pressure: float, tolerance_bara: float = 1e-3):
        self._target_pressure = target_pressure
        self._tolerance_bara = tolerance_bara

    def check(self, stream: FluidStream | None) -> TypeGuard[FluidStream]:
        if stream is None:
            return False
        return abs(stream.pressure_bara - self._target_pressure) <= self._tolerance_bara
