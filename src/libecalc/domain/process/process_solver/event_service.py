from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from libecalc.domain.process.process_solver.process_runner import Configuration
from libecalc.domain.process.process_system.process_unit import ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


@dataclass(frozen=True)
class ConfigurationAppliedEvent:
    """Published by ``TracingProcessRunner`` each time a configuration is
    applied to the process system.

    Attributes:
        configuration: The configuration that was applied.
    """

    configuration: Configuration


@dataclass(frozen=True)
class StreamPropagatedEvent:
    """Published by ``TracingProcessUnit`` each time a fluid stream is
    propagated through a process unit.

    Attributes:
        process_unit_id: The id of the process unit that propagated the stream.
        inlet_stream: The fluid stream entering the unit.
        outlet_stream: The fluid stream leaving the unit.
    """

    process_unit_id: ProcessUnitId
    inlet_stream: FluidStream
    outlet_stream: FluidStream


Event = Union[ConfigurationAppliedEvent, StreamPropagatedEvent]


class EventService:
    """A simple, synchronous event collector.

    Components publish events via :meth:`publish` and consumers retrieve
    them via :meth:`get_events`.  This is intentionally minimal — no
    async dispatch, no subscriptions — just an append-only log that can
    be inspected after a solve for visualization or debugging::

        events = EventService()
        tracer = TracingProcessRunner(inner_runner, events)
        # ... run a solve ...
        for event in events.get_events():
            print(event)
    """

    def __init__(self) -> None:
        self._events: list[Event] = []

    def publish(self, event: Event) -> None:
        """Append an event to the log."""
        self._events.append(event)

    def get_events(self) -> list[Event]:
        """Return a copy of all recorded events."""
        return list(self._events)

    def clear(self) -> None:
        """Discard all recorded events."""
        self._events.clear()
