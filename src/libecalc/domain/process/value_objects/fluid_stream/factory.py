from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from libecalc.common.fluid import FluidModel
from libecalc.domain.process.value_objects.fluid_stream import FluidStream
from libecalc.domain.process.value_objects.fluid_stream.thermo_system import ThermoSystemInterface


class FluidFactoryInterface(Protocol):
    """Factory interface for creating fluid streams and thermo systems from fluid models."""

    @property
    def fluid_model(self) -> FluidModel:
        """Get the fluid model used by this factory."""
        ...

    def create_thermo_system(self, pressure_bara: float, temperature_kelvin: float) -> ThermoSystemInterface:
        """Create a thermo system at specified conditions.

        Args:
            pressure_bara: Pressure in bara
            temperature_kelvin: Temperature in Kelvin

        Returns:
            A ThermoSystemInterface instance at the specified conditions
        """
        ...

    def create_stream_from_standard_rate(
        self, pressure_bara: float, temperature_kelvin: float, standard_rate: float
    ) -> FluidStream:
        """Create a fluid stream from standard volumetric rate.

        Args:
            pressure_bara: Pressure in bara
            temperature_kelvin: Temperature in Kelvin
            standard_rate: Volumetric flow rate at standard conditions [Sm³/day]

        Returns:
            A FluidStream instance
        """
        ...

    def create_stream_from_mass_rate(
        self, pressure_bara: float, temperature_kelvin: float, mass_rate: float
    ) -> FluidStream:
        """Create a fluid stream from mass rate.

        Args:
            pressure_bara: Pressure in bara
            temperature_kelvin: Temperature in Kelvin
            mass_rate: Mass flow rate [kg/h]

        Returns:
            A FluidStream instance
        """
        ...

    def standard_rate_to_mass_rate(self, standard_rate: float | NDArray[np.float64]) -> float | NDArray[np.float64]:
        """Convert standard volumetric rate to mass rate.

        Args:
            standard_rate: Volumetric flow rate at standard conditions [Sm³/day]

        Returns:
            Mass flow rate [kg/h]
        """
        ...

    def mass_rate_to_standard_rate(self, mass_rate: float | NDArray[np.float64]) -> float | NDArray[np.float64]:
        """Convert mass rate to standard volumetric rate.

        Args:
            mass_rate: Mass flow rate [kg/h]

        Returns:
            Volumetric flow rate at standard conditions [Sm³/day]
        """
        ...
