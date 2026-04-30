import abc
from typing import TypeGuard

from libecalc.process.fluid_stream.fluid_stream import FluidStream

EPSILON = 1e-5


class StreamConstraint(abc.ABC):
    @abc.abstractmethod
    def check(self, stream: FluidStream | None) -> TypeGuard[FluidStream]: ...


class PressureStreamConstraint(StreamConstraint):
    def __init__(self, target_pressure: float):
        self._target_pressure = target_pressure

    def check(self, stream: FluidStream | None) -> TypeGuard[FluidStream]:
        if stream is None:
            return False
        return self._target_pressure - EPSILON <= stream.pressure_bara <= self._target_pressure + EPSILON
