import abc

from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class ProcessUnit(abc.ABC):
    @abc.abstractmethod
    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream | None: ...
