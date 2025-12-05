"""Fluid: a fluid at a specific thermodynamic state.

This module defines the Fluid dataclass which represents a fluid with a specific
composition (FluidModel) at a specific thermodynamic state (FluidProperties).
"""

from __future__ import annotations

from dataclasses import dataclass

from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties


@dataclass(frozen=True)
class Fluid:
    """A fluid at a specific thermodynamic state (T/P).

    This frozen dataclass holds both the fluid model (composition + EoS) and the
    current thermodynamic properties. Flash methods use NeqSimFluidService internally
    and return new Fluid instances.

    Attributes:
        fluid_model: FluidModel containing composition and EoS model
        properties: FluidProperties containing all thermodynamic state data

    Example usage:
        # Create fluid via factory
        fluid = factory.create_fluid(pressure=40, temperature=300)

        # Flash to new conditions
        new_fluid = fluid.flash_pt(new_pressure, new_temperature)

        # Create stream from fluid
        stream = FluidStream(fluid=fluid, mass_rate_kg_per_h=1000)
    """

    fluid_model: FluidModel
    properties: FluidProperties

    # =========================================================================
    # Convenience properties delegating to fluid_model
    # =========================================================================

    @property
    def composition(self) -> FluidComposition:
        """Get the molar composition of the fluid."""
        return self.fluid_model.composition

    @property
    def eos_model(self) -> EoSModel:
        """Get the equation of state model."""
        return self.fluid_model.eos_model

    # =========================================================================
    # Convenience properties delegating to properties
    # =========================================================================

    @property
    def temperature_kelvin(self) -> float:
        """Get temperature [K]."""
        return self.properties.temperature_kelvin

    @property
    def pressure_bara(self) -> float:
        """Get pressure [bara]."""
        return self.properties.pressure_bara

    @property
    def density(self) -> float:
        """Get density [kg/m3]."""
        return self.properties.density

    @property
    def enthalpy_joule_per_kg(self) -> float:
        """Get specific enthalpy [J/kg]."""
        return self.properties.enthalpy_joule_per_kg

    @property
    def z(self) -> float:
        """Get compressibility factor [-]."""
        return self.properties.z

    @property
    def kappa(self) -> float:
        """Get isentropic exponent [-]."""
        return self.properties.kappa

    @property
    def molar_mass(self) -> float:
        """Get molar mass [kg/mol]."""
        return self.properties.molar_mass

    @property
    def standard_density_gas_phase_after_flash(self) -> float:
        """Get gas phase density at standard conditions [kg/Sm3]."""
        return self.properties.standard_density

    @property
    def vapor_fraction_molar(self) -> float:
        """Get molar vapor fraction [0-1]."""
        return self.properties.vapor_fraction_molar

    # =========================================================================
    # Flash methods - use NeqSimFluidService internally
    # =========================================================================

    def flash_pt(
        self,
        pressure_bara: float,
        temperature_kelvin: float,
        remove_liquid: bool = False,
    ) -> Fluid:
        """TP flash - returns new Fluid at given pressure and temperature.

        Args:
            pressure_bara: Target pressure [bara]
            temperature_kelvin: Target temperature [K]
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            New Fluid instance at the target conditions. If remove_liquid=True and
            liquid was present, the returned Fluid will have updated composition.
        """

        new_props, new_composition = NeqSimFluidService.instance().flash_pt(
            fluid_model=self.fluid_model,
            pressure_bara=pressure_bara,
            temperature_kelvin=temperature_kelvin,
            remove_liquid=remove_liquid,
        )
        new_fluid_model = FluidModel(composition=new_composition, eos_model=self.eos_model)
        return Fluid(fluid_model=new_fluid_model, properties=new_props)

    def flash_ph(
        self,
        pressure_bara: float,
        enthalpy_change_joule_per_kg: float,
        remove_liquid: bool = False,
    ) -> Fluid:
        """PH flash - returns new Fluid with enthalpy change applied.

        Args:
            pressure_bara: Target pressure [bara]
            enthalpy_change_joule_per_kg: Change in specific enthalpy [J/kg]
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            New Fluid instance at the resulting conditions. If remove_liquid=True and
            liquid was present, the returned Fluid will have updated composition.
        """

        target_enthalpy = self.properties.enthalpy_joule_per_kg + enthalpy_change_joule_per_kg
        new_props, new_composition = NeqSimFluidService.instance().flash_ph(
            fluid_model=self.fluid_model,
            pressure_bara=pressure_bara,
            target_enthalpy=target_enthalpy,
            remove_liquid=remove_liquid,
        )
        new_fluid_model = FluidModel(composition=new_composition, eos_model=self.eos_model)
        return Fluid(fluid_model=new_fluid_model, properties=new_props)
