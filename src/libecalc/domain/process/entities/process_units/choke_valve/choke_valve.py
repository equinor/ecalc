from __future__ import annotations

import uuid

from libecalc.domain.common import ID, SimpleEntityID
from libecalc.domain.process.entities.fluid_stream.fluid_stream import FluidStream
from libecalc.domain.process.entities.process_units.choke_valve.exceptions import (
    ChokeValveNotCalculatedException,
    InvalidPressureDropException,
    NegativePressureDropException,
    NoInletStreamException,
    NoInletStreamForCalculationException,
)


class ChokeValve:
    """
    Choke valve process unit that creates pressure drop.

    Simulates isenthalpic throttling process where:
    - Outlet pressure = inlet pressure - delta_P_bar
    - Enthalpy remains constant (isenthalpic process Δh = 0)
    - Temperature may change due to:
      - Joule-Thomson effect (real-gas non-ideality)
      - Phase transitions triggered by the lower pressure (condensation or vaporisation)

    Attributes:
        entity_id: Unique identifier for this choke valve
        delta_p_bar: Pressure drop across valve [bar]
    """

    def __init__(
        self,
        delta_p_bar: float,
        entity_id: ID | None = None,
        inlet_stream: FluidStream | None = None,
    ) -> None:
        """Initialize choke valve with pressure drop and optional ID.

        Args:
            delta_p_bar: Pressure drop across valve [bar]
            entity_id: Unique identifier (auto-generated if not provided)
            inlet_stream: FluidStream with inlet conditions (for backward compatibility)

        Raises:
            NegativePressureDropException: If delta_p_bar is negative
            InvalidPressureDropException: If outlet pressure would be negative (when inlet_stream provided)
        """
        if delta_p_bar < 0:
            raise NegativePressureDropException(delta_p_bar)

        # Validate outlet pressure if inlet stream is provided
        if inlet_stream is not None:
            outlet_pressure = inlet_stream.pressure_bara - delta_p_bar
            if outlet_pressure <= 0:
                raise InvalidPressureDropException(inlet_stream.pressure_bara, delta_p_bar)

        self._id = entity_id or SimpleEntityID(f"ChokeValve-{uuid.uuid4().hex[:8]}")
        self._delta_p_bar = delta_p_bar
        self._inlet_stream = inlet_stream
        self._outlet_stream: FluidStream | None = None
        self._calculated = False

    def get_id(self) -> ID:
        """Get the unique identifier for this choke valve."""
        return self._id

    @property
    def delta_p_bar(self) -> float:
        """Get the pressure drop across the valve [bar]."""
        return self._delta_p_bar

    @property
    def inlet_stream(self) -> FluidStream:
        """Get the inlet stream."""
        if self._inlet_stream is None:
            raise NoInletStreamException()
        return self._inlet_stream

    @property
    def outlet_stream(self) -> FluidStream:
        """
        Get the outlet stream after choking.

        Returns:
            FluidStream with reduced pressure and adjusted temperature

        Raises:
            RuntimeError: If calculate() has not been called yet
        """
        if self._outlet_stream is None:
            raise ChokeValveNotCalculatedException()
        return self._outlet_stream

    @property
    def is_calculated(self) -> bool:
        """Check if the choke valve calculation has been performed."""
        return self._calculated

    def set_inlet_stream(self, inlet_stream: FluidStream) -> None:
        """Set the inlet stream for graph-based workflows."""
        # Validate pressure drop won't cause negative outlet pressure
        outlet_pressure = inlet_stream.pressure_bara - self._delta_p_bar
        if outlet_pressure <= 0:
            raise InvalidPressureDropException(inlet_stream.pressure_bara, self._delta_p_bar)

        self._inlet_stream = inlet_stream
        self._calculated = False  # Reset calculation state

    def calculate(self) -> None:
        """
        Calculate the outlet stream conditions after throttling/choking.

        Raises:
            RuntimeError: If no inlet stream is available
        """
        if self._inlet_stream is None:
            raise NoInletStreamForCalculationException()

        outlet_pressure = self._inlet_stream.pressure_bara - self._delta_p_bar

        self._outlet_stream = self._inlet_stream.create_stream_with_new_pressure_and_enthalpy_change(
            pressure_bara=outlet_pressure,
            enthalpy_change=0.0,  # Isenthalpic process
            remove_liquid=False,
        )
        self._calculated = True
