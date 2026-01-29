import abc

from libecalc.domain.process.value_objects.fluid_stream import FluidStream

PORT_ID = str


class ProcessSystem(abc.ABC):
    @abc.abstractmethod
    def propagate_streams(self, inlet_streams: dict[PORT_ID, FluidStream]) -> dict[PORT_ID, FluidStream]: ...
