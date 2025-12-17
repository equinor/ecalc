"""Stateless service interface for fluid thermodynamic operations.

This module defines the FluidServiceInterface Protocol which provides
a clean abstraction layer between domain models and infrastructure.

All methods take fluid_model as parameter - the service has no bound state.
Designed to work as a singleton for global caching.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from libecalc.domain.process.value_objects.fluid_stream.fluid import Fluid
    from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidComposition, FluidModel
    from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties
    from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream


class FluidServiceInterface(Protocol):
    """Stateless service interface for fluid thermodynamic operations.

    All methods take fluid_model as parameter - service has no bound state.
    Designed to work as a singleton for global caching.
    """

    # === Flash Operations ===

    def flash_pt(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
        remove_liquid: bool = False,
    ) -> tuple[FluidProperties, FluidComposition]:
        """TP flash returning properties and updated composition.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            Tuple of (FluidProperties, FluidComposition) where composition may be
            updated to gas-phase composition if remove_liquid=True and liquid was present.
        """
        ...

    def flash_ph(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        target_enthalpy: float,
        remove_liquid: bool = False,
    ) -> tuple[FluidProperties, FluidComposition]:
        """PH flash to target pressure and enthalpy.

        Note: The target_enthalpy is reference-state dependent. Thermodynamic packages
        may use arbitrary enthalpy reference states, so the caller must ensure that
        target_enthalpy was computed from enthalpy values obtained from the same
        EoS/fluid model session. Mixing enthalpy values from different thermodynamic
        packages or sessions may produce incorrect results.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            target_enthalpy: Target specific enthalpy in J/kg (must be from same EoS session)
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            Tuple of (FluidProperties, FluidComposition) where composition may be
            updated to gas-phase composition if remove_liquid=True and liquid was present.
        """
        ...

    # === Convenience Methods ===

    def create_fluid(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
        remove_liquid: bool = False,
    ) -> Fluid:
        """Create a Fluid at specified conditions via TP flash.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            New Fluid instance at the specified conditions. If remove_liquid=True and
            liquid was present, the returned Fluid will have updated composition.
        """
        ...

    def create_stream_from_standard_rate(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
        standard_rate_m3_per_day: float,
    ) -> FluidStream:
        """Create a fluid stream from standard volumetric rate.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin
            standard_rate_m3_per_day: Volumetric flow rate at standard conditions [Sm3/day]

        Returns:
            A FluidStream instance
        """
        ...

    def create_stream_from_mass_rate(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
        mass_rate_kg_per_h: float,
    ) -> FluidStream:
        """Create a fluid stream from mass rate.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin
            mass_rate_kg_per_h: Mass flow rate [kg/h]

        Returns:
            A FluidStream instance
        """
        ...

    # === Rate Conversions ===

    def standard_rate_to_mass_rate(
        self,
        fluid_model: FluidModel,
        standard_rate_m3_per_day: float,
    ) -> float:
        """Convert standard volumetric rate to mass rate.

        Args:
            fluid_model: The fluid model (composition + EoS)
            standard_rate_m3_per_day: Volumetric flow rate at standard conditions [Sm3/day]

        Returns:
            Mass flow rate [kg/h]
        """
        ...

    def mass_rate_to_standard_rate(
        self,
        fluid_model: FluidModel,
        mass_rate_kg_per_h: float,
    ) -> float:
        """Convert mass rate to standard volumetric rate.

        Args:
            fluid_model: The fluid model (composition + EoS)
            mass_rate_kg_per_h: Mass flow rate [kg/h]

        Returns:
            Volumetric flow rate at standard conditions [Sm3/day]
        """
        ...
