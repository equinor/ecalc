from __future__ import annotations

import logging
from collections.abc import Mapping
from types import MappingProxyType

from libecalc.domain.common import ID
from libecalc.domain.process.entities.base import Entity
from libecalc.domain.process.entities.process_units.choke_valve.exceptions import (
    ChokeValveNotCalculatedException,
    InvalidPressureDropException,
    NegativePressureDropException,
)
from libecalc.domain.process.entities.process_units.exceptions import NoInletStreamException
from libecalc.domain.process.entities.process_units.port_names import PortName, SingleIO
from libecalc.domain.process.entities.process_units.protocols import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream

logger = logging.getLogger(__name__)


class ChokeValve(Entity[ID], ProcessUnit):
    """
    Choke valve process unit that creates pressure drop.

    Simulates isenthalpic throttling process where:
    - Outlet pressure = inlet pressure - delta_P_bar
    - Enthalpy remains constant (isenthalpic process Δh = 0)
    - Temperature may change due to:
      - Joule-Thomson effect (real-gas non-ideality)
      - Phase transitions triggered by the lower pressure
    Choked flow is handled by ensuring that the outlet pressure does not drop below pressure corresponding to critical pressure ratio.
    Note: this is a simplified choke flow handling that assumes pure phase ideal gas.

    Attributes:
        entity_id: Unique identifier for this choke valve
        delta_p_bar: Pressure drop across valve [bar]
    """

    def __init__(self, entity_id: ID, delta_p_bar: float = 0.0) -> None:
        """Initialize choke valve with pressure drop.

        Args:
            entity_id: Unique identifier for this choke valve
            delta_p_bar: Pressure drop across valve [bar], defaults to 0.0

        Raises:
            NegativePressureDropException: If delta_p_bar is negative
        """
        super().__init__(entity_id)
        # Initialize ports and calculation state
        self._inlet_ports: dict[PortName, FluidStream | None] = {SingleIO.INLET: None}
        self._outlet_ports: dict[PortName, FluidStream | None] = {SingleIO.OUTLET: None}
        self._calculated = False
        self._delta_p_bar = 0.0  # Default value
        self.delta_p_bar = delta_p_bar

    @property
    def delta_p_bar(self) -> float:
        """Get the pressure drop across the valve [bar]."""
        return self._delta_p_bar

    @delta_p_bar.setter
    def delta_p_bar(self, value: float) -> None:
        """Set the pressure drop across the valve [bar].

        Args:
            value: The new pressure drop value in bar.

        Raises:
            NegativePressureDropException: If value is negative.
        """
        if value < 0:
            raise NegativePressureDropException(value)

        self._delta_p_bar = value
        logger.warning(f"Outlet stream is set to None due to new delta_p_bar: {value:.2f} bar. ")
        self._outlet_ports[SingleIO.OUTLET] = None
        self._calculated = False

    @property
    def is_calculated(self) -> bool:
        """Check if the choke valve calculation has been performed."""
        return self._calculated

    def get_inlet_ports(self) -> Mapping[PortName, FluidStream | None]:
        """Get all inlet ports and their connected streams."""
        return MappingProxyType(self._inlet_ports)

    def get_outlet_ports(self) -> Mapping[PortName, FluidStream | None]:
        """Get all outlet ports and their connected streams."""
        return MappingProxyType(self._outlet_ports)

    def connect_inlet_port(self, port_name: PortName, stream: FluidStream) -> None:
        """Connect a fluid stream to the specified inlet port."""
        if port_name not in self._inlet_ports:
            raise ValueError(f"Unknown inlet port: {port_name}")

        # Validate pressure drop won't cause negative outlet pressure
        outlet_pressure = stream.pressure_bara - self._delta_p_bar
        if outlet_pressure <= 0:
            raise InvalidPressureDropException(stream.pressure_bara, self._delta_p_bar)

        self._inlet_ports[port_name] = stream
        self._outlet_ports[SingleIO.OUTLET] = None
        self._calculated = False

    def get_stream_from_port(self, port: PortName) -> FluidStream:
        """
        Get the stream for the given port.

        Args:
            port: The port name to get the stream from

        Returns:
            The fluid stream connected to the port

        Raises:
            ValueError: If the port name is unknown
            NoInletStreamException: If no stream is connected to an inlet port
            ChokeValveNotCalculatedException: If the outlet port is accessed but the valve has not been calculated
        """
        if port in self._inlet_ports:
            stream = self._inlet_ports[port]
            if stream is None:
                raise NoInletStreamException()
            return stream
        elif port in self._outlet_ports:
            stream = self._outlet_ports[port]
            if stream is None:
                raise ChokeValveNotCalculatedException()
            return stream
        else:
            raise ValueError(f"Unknown port: {port}")

    def calculate(self) -> None:
        """
        Calculate the outlet stream conditions after throttling/choking.

        Raises:
            NoInletStreamForCalculationException: If no inlet stream is available
        """
        inlet_stream = self._inlet_ports[SingleIO.INLET]
        if inlet_stream is None:
            raise NoInletStreamException()

        kappa = inlet_stream.kappa
        pressure_ratio_crit = (2 / (kappa + 1)) ** (kappa / (kappa - 1))  # Critical pressure ratio for choked flow
        p_min = inlet_stream.pressure_bara * pressure_ratio_crit  # Minimum outlet pressure for choked flow
        if inlet_stream.pressure_bara - self.delta_p_bar < p_min:
            logger.warning(
                f"Choked flow condition met: Inlet pressure {inlet_stream.pressure_bara:.2f} bara, "
                f"delta P {self.delta_p_bar:.2f} bar, "
                f"critical pressure ratio {pressure_ratio_crit:.2f}, "
                f"minimum outlet pressure {p_min:.2f} bara."
                f" Outlet pressure will be set to minimum achievable value for choked gas flow {p_min:.2f} bara."
            )
        # If choked flow, set outlet pressure to critical value (max of p_min and the calculated pressure)
        outlet_pressure = max(p_min, inlet_stream.pressure_bara - self.delta_p_bar)

        outlet_stream = inlet_stream.create_stream_with_new_pressure_and_enthalpy_change(
            pressure_bara=outlet_pressure,
            enthalpy_change=0.0,  # Isenthalpic process
            remove_liquid=False,
        )
        self._outlet_ports[SingleIO.OUTLET] = outlet_stream
        self._calculated = True

    # Convenience methods specific to this unit ->
    def connect_inlet_stream(self, stream: FluidStream) -> None:
        """Connect a fluid stream to the inlet port."""
        self.connect_inlet_port(SingleIO.INLET, stream)

    def get_inlet_stream(self) -> FluidStream:
        """Get the inlet stream connected to the inlet port."""
        stream = self._inlet_ports[SingleIO.INLET]
        if stream is None:
            raise NoInletStreamException()
        return stream

    def get_outlet_stream(self) -> FluidStream:
        """Get the outlet stream after calculation."""
        stream = self._outlet_ports[SingleIO.OUTLET]
        if stream is None:
            raise ChokeValveNotCalculatedException()
        return stream
