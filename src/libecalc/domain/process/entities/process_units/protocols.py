from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream


@runtime_checkable
class ProcessUnit(Protocol):
    """Base protocol for process units with port-based stream connections."""

    def calculate(self) -> None:
        """Calculate the process unit output conditions."""
        ...

    @property
    def is_calculated(self) -> bool:
        """Check if the process unit calculation has been performed."""
        ...

    def get_inlet_ports(self) -> Mapping[str, FluidStream | None]:
        """Get all inlet ports and their connected streams."""
        ...

    def get_outlet_ports(self) -> Mapping[str, FluidStream | None]:
        """Get all outlet ports and their connected streams."""
        ...

    def connect_inlet_port(self, port_name: str, stream: FluidStream) -> None:
        """Connect a fluid stream to the specified inlet port."""
        ...


class HasInletStream(Protocol):
    """Protocol for process units with a single inlet stream."""

    @property
    def inlet_stream(self) -> FluidStream:
        """Get the inlet stream."""
        ...


class HasOutletStream(Protocol):
    """Protocol for process units with a single outlet stream."""

    @property
    def outlet_stream(self) -> FluidStream:
        """Get the outlet stream."""
        ...


class HasInletStreams(Protocol):
    """Protocol for process units with multiple inlet streams."""

    @property
    def inlet_streams(self) -> list[FluidStream]:
        """Get the inlet streams."""
        ...


class HasOutletStreams(Protocol):
    """Protocol for process units with multiple outlet streams."""

    @property
    def outlet_streams(self) -> list[FluidStream]:
        """Get the outlet streams."""
        ...


class SingleInletSingleOutlet(ProcessUnit, HasInletStream, HasOutletStream):
    """Process unit with one inlet stream and one outlet stream.

    Examples: ChokeValve, Pump, Compressor, Heat Exchanger
    """

    pass


class MultipleInletSingleOutlet(ProcessUnit, HasInletStreams, HasOutletStream):
    """Process unit with multiple inlet streams and one outlet stream.

    Examples: Mixer, (Multi-stream Heat Exchanger)
    """

    pass


class SingleInletMultipleOutlet(ProcessUnit, HasInletStream, HasOutletStreams):
    """Process unit with one inlet stream and multiple outlet streams.

    Examples: Separator, Splitter, Scrubber
    """

    pass


class MultipleInletMultipleOutlet(ProcessUnit, HasInletStreams, HasOutletStreams):
    """Process unit with multiple inlet streams and multiple outlet streams.

    Examples: Complex Units
    """

    pass
