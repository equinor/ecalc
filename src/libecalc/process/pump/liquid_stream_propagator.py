import abc

from libecalc.process.pump.liquid_stream import LiquidStream


class LiquidStreamPropagator(abc.ABC):
    @abc.abstractmethod
    def propagate_stream(self, inlet_stream: LiquidStream) -> LiquidStream: ...
