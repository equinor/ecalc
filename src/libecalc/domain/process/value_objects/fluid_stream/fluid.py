"""Fluid protocol for decoupling domain from specific thermodynamic providers.

This module defines the Fluid protocol which represents a fluid at a specific
thermodynamic state. Implementations (e.g., NeqSimFluidFactory) live in the
infrastructure layer, enabling future alternative providers (CoolProp, REFPROP, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel
    from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties
    from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream


class Fluid(Protocol):
    """Protocol defining a fluid at a specific thermodynamic state.

    This is the domain interface - implementations live in infrastructure.
    Enables decoupling from NeqSim (can add CoolProp, REFPROP, etc.).

    A Fluid carries both the fluid model (composition + EoS) and the current
    thermodynamic properties (P, T, density, etc.). Flash operations return
    new Fluid instances at the target conditions.

    Example usage:
        fluid = NeqSimFluidFactory.create(fluid_model, P, T)
        new_fluid = fluid.flash_pt(new_P, new_T)
        stream = fluid.to_stream(mass_rate_kg_per_h=1000)
    """

    @property
    def fluid_model(self) -> FluidModel:
        """Get the fluid model (composition + EoS)."""
        ...

    @property
    def fluid_properties(self) -> FluidProperties:
        """Get the current thermodynamic properties."""
        ...

    def flash_pt(
        self,
        pressure_bara: float,
        temperature_kelvin: float,
        remove_liquid: bool = False,
    ) -> Fluid:
        """TP flash - returns new Fluid at given conditions.

        Args:
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            New Fluid instance at the target conditions
        """
        ...

    def flash_ph(
        self,
        pressure_bara: float,
        enthalpy_change_joule_per_kg: float,
        remove_liquid: bool = False,
    ) -> Fluid:
        """PH flash - returns new Fluid with enthalpy change applied.

        Args:
            pressure_bara: Target pressure in bara
            enthalpy_change_joule_per_kg: Change in specific enthalpy [J/kg]
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            New Fluid instance at the resulting conditions
        """
        ...

    def to_stream(
        self,
        *,
        mass_rate_kg_per_h: float | None = None,
        standard_rate_m3_per_day: float | None = None,
    ) -> FluidStream:
        """Create a FluidStream from this fluid with specified rate.

        Args:
            mass_rate_kg_per_h: Mass flow rate [kg/h]
            standard_rate_m3_per_day: Volumetric flow rate at standard conditions [Sm3/day]

        Returns:
            FluidStream with the fluid's properties and specified rate

        Raises:
            ValueError: If neither rate is specified
        """
        ...

    def standard_rate_to_mass_rate(self, standard_rate: float) -> float:
        """Convert standard volumetric rate to mass rate.

        Args:
            standard_rate: Volumetric flow rate at standard conditions [Sm3/day]

        Returns:
            Mass flow rate [kg/h]
        """
        ...

    def mass_rate_to_standard_rate(self, mass_rate: float) -> float:
        """Convert mass rate to standard volumetric rate.

        Args:
            mass_rate: Mass flow rate [kg/h]

        Returns:
            Volumetric flow rate at standard conditions [Sm3/day]
        """
        ...
