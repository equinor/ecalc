import abc

from libecalc.domain.process.process_events.process_event_decorator import monitor_stream
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class ProcessUnit(abc.ABC):
    @monitor_stream
    @abc.abstractmethod
    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream: ...
