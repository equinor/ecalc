import abc

from libecalc.process.fluid_stream.fluid_stream import FluidStream


class StreamDistribution(abc.ABC):
    @abc.abstractmethod
    def get_number_of_streams(self) -> int: ...

    @abc.abstractmethod
    def get_streams(self) -> list[FluidStream]: ...
