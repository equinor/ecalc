from __future__ import annotations

from typing import Protocol

from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream


class ProcessUnit(Protocol):
    """Base protocol for all process units."""

    def calculate(self) -> None:
        """Calculate the process unit output conditions."""
        ...

    @property
    def is_calculated(self) -> bool:
        """Check if the process unit calculation has been performed."""
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
