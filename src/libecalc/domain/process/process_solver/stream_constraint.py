import abc
from typing import TypeGuard

from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


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
