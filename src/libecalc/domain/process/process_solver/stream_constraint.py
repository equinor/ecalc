import abc
from typing import TypeGuard

from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class StreamConstraint(abc.ABC):
    @abc.abstractmethod
    def check(self, stream: FluidStream | None) -> TypeGuard[FluidStream]: ...
