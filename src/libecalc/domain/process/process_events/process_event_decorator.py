"""
A simple and quick start to fetch and store relevant process events in a general way, without having to change the process system or units too much.

"""

import functools
from collections.abc import Callable
from typing import Any

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.domain.process.process_events.process_event import ProcessEvent
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

type T = Any


def monitor_stream(
    method: Callable[..., FluidStream],
) -> Callable[..., FluidStream]:
    """Decorator to monitor and publish process events for methods with inlet_stream parameter.

    Currently implemented very simplistically for internal use of printing events, to debug and read state at different places in the process.
    """

    @functools.wraps(method)
    def wrapper(self, inlet_stream: FluidStream) -> FluidStream:
        # Verify the instance implements the required interface

        if not isinstance(inlet_stream, FluidStream):
            raise ProgrammingError(f"Expected inlet_stream to be of type FluidStream, got {type(inlet_stream)}")

        # Publish inlet stream event
        inlet_event = ProcessEvent(
            category="stream",
            name=self.__class__.__name__,
            state=inlet_stream,
            loc="BEFORE",
        )
        # print(inlet_event)

        # Execute the actual method
        outlet_stream = method(self, inlet_stream)

        # Publish outlet stream event
        outlet_event = ProcessEvent(category="stream", name=self.__class__.__name__, state=outlet_stream, loc="AFTER")
        # print(outlet_event)

        print(f"Actual event, ie. the delta between inlet and outlet: {outlet_event.state - inlet_event.state}")

        return outlet_stream

    return wrapper
