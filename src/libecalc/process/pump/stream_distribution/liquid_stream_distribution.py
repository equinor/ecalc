import abc

from libecalc.process.pump.liquid_stream import LiquidStream


class LiquidStreamDistribution(abc.ABC):
    @abc.abstractmethod
    def get_number_of_streams(self) -> int: ...

    @abc.abstractmethod
    def get_streams(self) -> list[LiquidStream]: ...
