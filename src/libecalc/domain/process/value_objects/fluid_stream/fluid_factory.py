from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from libecalc.domain.process.value_objects.fluid_stream import FluidStream
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel
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
        self, pressure_bara: float, temperature_kelvin: float, standard_rate_m3_per_day: float
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
        self, pressure_bara: float, temperature_kelvin: float, mass_rate_kg_per_h: float
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

    def standard_rate_to_mass_rate(
        self, standard_rate_m3_per_day: float | NDArray[np.float64]
    ) -> float | NDArray[np.float64]:
        """Convert standard volumetric rate to mass rate.

        Args:
            standard_rate: Volumetric flow rate at standard conditions [Sm³/day]

        Returns:
            Mass flow rate [kg/h]
        """
        ...

    def mass_rate_to_standard_rate(
        self, mass_rate_kg_per_h: float | NDArray[np.float64]
    ) -> float | NDArray[np.float64]:
        """Convert mass rate to standard volumetric rate.

        Args:
            mass_rate: Mass flow rate [kg/h]

        Returns:
            Volumetric flow rate at standard conditions [Sm³/day]
        """
        ...

    def create_fluid_factory_from_fluid_model(self, fluid_model: FluidModel) -> FluidFactoryInterface:
        """Create a new fluid factory from a fluid model.

        Args:
            fluid_model: The fluid model to use for the new factory

        Returns:
            A new FluidFactoryInterface instance with the given fluid model
        """
        ...
