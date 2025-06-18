from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from libecalc.domain.process.entities.process_units.port_names import PortName
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

    def get_inlet_ports(self) -> Mapping[PortName, FluidStream | None]:
        """Get all inlet ports and their connected streams."""
        ...

    def get_outlet_ports(self) -> Mapping[PortName, FluidStream | None]:
        """Get all outlet ports and their connected streams."""
        ...

    def connect_inlet_port(self, port_name: PortName, stream: FluidStream) -> None:
        """Connect a fluid stream to the specified inlet port."""
        ...

    def get_stream_from_port(self, port: PortName) -> FluidStream:
        """
        Get the stream for the given port.
        For inlet ports, if no stream is connected, NoInletStreamException is raised.
        For outlet ports, if the process has not been calculated, a "<UnitName>NotCalculatedException" is raised.
        """
        ...
