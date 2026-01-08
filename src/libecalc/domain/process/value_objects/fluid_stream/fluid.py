"""Fluid: a fluid at a specific thermodynamic state.

This module defines the Fluid dataclass which represents a fluid with a specific
composition (FluidModel) at a specific thermodynamic state (FluidProperties).

Fluid is a pure data holder - all flash operations should be performed via
FluidService interface, which can be obtained from the infrastructure layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties


@dataclass(frozen=True)
class Fluid:
    """A fluid at a specific thermodynamic state (T/P).

    This is a pure data holder containing a FluidModel (composition + EoS) and
    FluidProperties (thermodynamic state). Flash operations should be performed
    via FluidService interface, not on this class.

    Attributes:
        fluid_model: FluidModel containing composition and EoS model
        properties: FluidProperties containing all thermodynamic state data

    Example usage:
        # Create fluid via service
        fluid = fluid_service.create_fluid(fluid_model, pressure=40, temperature=300)

        # Flash to new conditions via service
        new_fluid = fluid_service.create_fluid(
            fluid.fluid_model, new_pressure, new_temperature
        )

        # Create stream from fluid
        stream = FluidStream(fluid=fluid, mass_rate_kg_per_h=1000)
    """

    fluid_model: FluidModel
    properties: FluidProperties

    # Convenience properties delegating to fluid_model ->
    @property
    def composition(self) -> FluidComposition:
        """Get the molar composition of the fluid."""
        return self.fluid_model.composition

    @property
    def eos_model(self) -> EoSModel:
        """Get the equation of state model."""
        return self.fluid_model.eos_model

    # Convenience properties delegating to properties ->
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
