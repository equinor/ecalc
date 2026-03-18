from __future__ import annotations

from libecalc.domain.process.process_solver.event_service import EventService, StreamPropagatedEvent
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class TracingProcessUnit(ProcessUnit):
    """A ``ProcessUnit`` wrapper that publishes a
    :class:`StreamPropagatedEvent` to an :class:`EventService` each time
    a fluid stream is propagated through the wrapped unit.

    All other calls are forwarded transparently to the inner unit.

    Example::

        events = EventService()
        choke = Choke(...)
        traced_choke = TracingProcessUnit(choke, events)
        # use traced_choke wherever the original choke was used
    """

    def __init__(self, inner: ProcessUnit, event_service: EventService) -> None:
        self._inner = inner
        self._event_service = event_service

    def get_id(self) -> ProcessUnitId:
        return self._inner.get_id()

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        outlet_stream = self._inner.propagate_stream(inlet_stream=inlet_stream)
        self._event_service.publish(
            StreamPropagatedEvent(
                process_unit_id=self._inner.get_id(),
                inlet_stream=inlet_stream,
                outlet_stream=outlet_stream,
            )
        )
        return outlet_stream
