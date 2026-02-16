"""
A process event is currently defined as a change in the process system that
already occurred, mainly for logging and tracking purposes.

We will initially "monitor" the stream, but we may want to store other states
as well, such as the final state of a process system or unit after we have found
a solution, or all failed attempts (and why).

An event is immutable once created.
"""

from dataclasses import dataclass, field
from typing import ClassVar, Literal
from uuid import UUID, uuid4

from libecalc.domain.process.value_objects.fluid_stream import (
    FluidStream,
)


@dataclass(frozen=True)
class ProcessEvent:
    _tick_counter: ClassVar[int] = 0  # shared counter across all instances

    # TODO: Should we change to UUID7 that is more db friendly?
    category: Literal["stream"]  # simple way of categorizing events, can be extended later
    # process_system_id: UUID  # since the processystem is the aggregate, it belongs to that
    # process_unit_id: UUID | None  # optional, since not all events are tied to a unit
    state: FluidStream  # we start by storing the whole state of the stream object (for simplicity)
    eventId: UUID = field(
        default_factory=uuid4
    )  # unique identifier for the event, since we need to store and identify it
    __tick: int = field(
        default_factory=lambda: ProcessEvent._get_next_tick()
    )  # timestamp is not relevant, but we want a chronological order of events
    loc: str = Literal["BEFORE", "AFTER"]
    name: str = ""  # Temp name of system or unit

    @classmethod
    def _get_next_tick(cls) -> int:
        """Get the next tick value and increment the counter."""
        current_tick = cls._tick_counter
        cls._tick_counter += 1
        return current_tick

    @property
    def tick(self) -> int:
        """Get the tick value of this event."""
        return self.__tick

    # Not sure if we need this, but it can be useful for testing or resetting the state for a new process run
    @classmethod
    def reset_tick_counter(cls) -> None:
        """Reset the tick counter to 0."""
        cls._tick_counter = 0

    def __repr__(self) -> str:
        return f"ProcessEvent(category={self.category}, eventId={self.eventId}, tick={self.__tick}, loc={self.loc}, name={self.name}, state={self.state})"

    def __str__(self) -> str:
        return self.__repr__()
