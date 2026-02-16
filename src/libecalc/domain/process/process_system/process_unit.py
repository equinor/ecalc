import abc

from libecalc.domain.process.process_events.process_event_decorator import monitor_stream
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class ProcessUnit(abc.ABC):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Force decorator to be applied to the propagate_stream method of all subclasses
        cls.propagate_stream = monitor_stream(cls.propagate_stream)

    @monitor_stream
    @abc.abstractmethod
    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream: ...
