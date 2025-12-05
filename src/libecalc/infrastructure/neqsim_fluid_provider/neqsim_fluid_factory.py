"""NeqSim implementation of the FluidFactoryInterface.

This module provides NeqSimFluidFactory, a factory for creating Fluid instances
using NeqSim for thermodynamic calculations via NeqSimFluidService.
"""

from __future__ import annotations

from functools import cached_property

import numpy as np
from numpy.typing import NDArray

from libecalc.common.units import UnitConstants
from libecalc.domain.process.value_objects.fluid_stream.fluid import Fluid
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream


class NeqSimFluidFactory:
    """Factory for creating Fluid instances via NeqSim.

    This factory stores a fluid model and provides methods to create Fluid
    instances at specific conditions. It also provides rate conversion utilities.

    Example usage:
        # Create factory for a fluid model
        factory = NeqSimFluidFactory(fluid_model)

        # Create fluid at conditions
        fluid = factory.create_fluid(pressure_bara=40, temperature_kelvin=300)

        # Create stream from fluid
        stream = FluidStream(fluid=fluid, mass_rate_kg_per_h=1000)

        # Or use convenience method
        stream = factory.create_stream_from_standard_rate(40, 300, 1000)

        # Rate conversions
        mass_rate = factory.standard_rate_to_mass_rate(1000)  # Sm3/day -> kg/h
    """

    def __init__(self, fluid_model: FluidModel) -> None:
        """Initialize factory with a fluid model.

        Args:
            fluid_model: The fluid model (composition + EoS) to use for flash calculations
        """
        self._fluid_model = fluid_model

    @property
    def fluid_model(self) -> FluidModel:
        """Get the fluid model used by this factory."""
        return self._fluid_model

    @cached_property
    def standard_density(self) -> float:
        """Get standard density for rate conversions (lazily computed)."""
        fluid = self.create_fluid(
            pressure_bara=UnitConstants.STANDARD_PRESSURE_BARA,
            temperature_kelvin=UnitConstants.STANDARD_TEMPERATURE_KELVIN,
        )
        return fluid.standard_density_gas_phase_after_flash

    def create_fluid(
        self,
        pressure_bara: float,
        temperature_kelvin: float,
        remove_liquid: bool = False,
    ) -> Fluid:
        """Create a Fluid at specified conditions via TP flash.

        Args:
            pressure_bara: Pressure [bara]
            temperature_kelvin: Temperature [K]
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            New Fluid instance at the specified conditions. If remove_liquid=True and
            liquid was present, the returned Fluid will have updated composition.
        """
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        props, new_composition = NeqSimFluidService.instance().flash_pt(
            fluid_model=self._fluid_model,
            pressure_bara=pressure_bara,
            temperature_kelvin=temperature_kelvin,
            remove_liquid=remove_liquid,
        )
        new_fluid_model = FluidModel(composition=new_composition, eos_model=self._fluid_model.eos_model)
        return Fluid(fluid_model=new_fluid_model, properties=props)

    def create_stream_from_standard_rate(
        self,
        pressure_bara: float,
        temperature_kelvin: float,
        standard_rate_m3_per_day: float,
        remove_liquid: bool = False,
    ) -> FluidStream:
        """Create a fluid stream at conditions from standard volumetric rate.

        Args:
            pressure_bara: Pressure [bara]
            temperature_kelvin: Temperature [K]
            standard_rate_m3_per_day: Volumetric flow rate at standard conditions [Sm3/day]
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            A FluidStream instance
        """
        fluid = self.create_fluid(pressure_bara, temperature_kelvin, remove_liquid)
        return FluidStream.from_standard_rate(
            standard_rate_m3_per_day=standard_rate_m3_per_day,
            fluid_model=fluid.fluid_model,
            fluid_properties=fluid.properties,
        )

    def create_stream_from_mass_rate(
        self,
        pressure_bara: float,
        temperature_kelvin: float,
        mass_rate_kg_per_h: float,
        remove_liquid: bool = False,
    ) -> FluidStream:
        """Create a fluid stream at conditions from mass rate.

        Args:
            pressure_bara: Pressure [bara]
            temperature_kelvin: Temperature [K]
            mass_rate_kg_per_h: Mass flow rate [kg/h]
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            A FluidStream instance
        """
        fluid = self.create_fluid(pressure_bara, temperature_kelvin, remove_liquid)
        return FluidStream(fluid=fluid, mass_rate_kg_per_h=mass_rate_kg_per_h)

    def standard_rate_to_mass_rate(
        self, standard_rate_m3_per_day: float | NDArray[np.float64]
    ) -> float | NDArray[np.float64]:
        """Convert standard volumetric rate to mass rate.

        Args:
            standard_rate_m3_per_day: Volumetric flow rate at standard conditions [Sm3/day]

        Returns:
            Mass flow rate [kg/h]
        """
        mass_rate_kg_per_hour = standard_rate_m3_per_day * self.standard_density / UnitConstants.HOURS_PER_DAY
        if isinstance(mass_rate_kg_per_hour, np.ndarray):
            return np.array(mass_rate_kg_per_hour)
        return float(mass_rate_kg_per_hour)

    def mass_rate_to_standard_rate(
        self, mass_rate_kg_per_h: float | NDArray[np.float64]
    ) -> float | NDArray[np.float64]:
        """Convert mass rate to standard volumetric rate.

        Args:
            mass_rate_kg_per_h: Mass flow rate [kg/h]

        Returns:
            Volumetric flow rate at standard conditions [Sm3/day]
        """
        standard_rate = mass_rate_kg_per_h / self.standard_density * UnitConstants.HOURS_PER_DAY
        if isinstance(standard_rate, np.ndarray):
            return np.array(standard_rate)
        return float(standard_rate)

    # =========================================================================
    # Backwards compatibility methods
    # =========================================================================

    def get_properties(
        self, pressure_bara: float, temperature_kelvin: float, remove_liquid: bool = False
    ) -> FluidProperties:
        """Get fluid properties at specified conditions.

        DEPRECATED: Use create_fluid() instead and access .properties.

        Args:
            pressure_bara: Pressure [bara]
            temperature_kelvin: Temperature [K]
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            FluidProperties at the specified conditions
        """
        return self.create_fluid(pressure_bara, temperature_kelvin, remove_liquid).properties

    def create_fluid_factory_from_fluid_model(self, fluid_model: FluidModel) -> NeqSimFluidFactory:
        """Create a new fluid factory from a fluid model.

        Args:
            fluid_model: The fluid model to use for the new factory

        Returns:
            A new NeqSimFluidFactory instance with the given fluid model
        """
        return NeqSimFluidFactory(fluid_model)

    @classmethod
    def from_fluid_model(cls, fluid_model: FluidModel) -> NeqSimFluidFactory:
        """Create a factory from a fluid model.

        DEPRECATED: Use NeqSimFluidFactory(fluid_model) instead.

        Args:
            fluid_model: The fluid model (composition + EoS)

        Returns:
            A new NeqSimFluidFactory instance
        """
        return cls(fluid_model)
