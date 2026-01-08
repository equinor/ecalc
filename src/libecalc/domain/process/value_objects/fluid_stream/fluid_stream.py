"""FluidStream: a fluid stream with flow rate.

This module defines the FluidStream dataclass which represents a fluid flow
at a specific thermodynamic state with a mass flow rate.

FluidStream is a pure data holder - all flash operations should be performed via
FluidService interface, and a new FluidStream created with with_new_fluid().
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from libecalc.common.units import UnitConstants
from libecalc.domain.process.value_objects.fluid_stream.exceptions import NegativeMassRateException
from libecalc.domain.process.value_objects.fluid_stream.fluid import Fluid
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidComposition, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties
from libecalc.domain.process.value_objects.fluid_stream.process_conditions import ProcessConditions


@dataclass(frozen=True)
class FluidStream:
    """Represents a fluid stream with thermodynamic properties and a flow rate.

    This is a pure dataclass containing a Fluid (at specific T/P state) and a mass rate.
    All flash operations should be performed via FluidService interface, then use
    with_new_fluid() to create a new stream with the updated fluid.

    Attributes:
        fluid: Fluid containing fluid_model and properties
        mass_rate_kg_per_h: Mass flow rate [kg/h]

    Example usage:
        # Create stream from fluid
        stream = FluidStream(fluid=fluid, mass_rate_kg_per_h=1000)

        # Flash to new conditions via service, then create new stream
        new_fluid = fluid_service.create_fluid(
            stream.fluid_model, new_pressure, new_temperature
        )
        new_stream = stream.with_new_fluid(new_fluid)

        # Change rate only
        modified_stream = stream.with_mass_rate(new_rate)
    """

    fluid: Fluid
    mass_rate_kg_per_h: float

    def __post_init__(self):
        """Validate stream properties"""
        if self.mass_rate_kg_per_h < 0:
            raise NegativeMassRateException(self.mass_rate_kg_per_h)

    # Convenience properties delegating to fluid ->
    @property
    def fluid_model(self) -> FluidModel:
        """Get the fluid model (composition + EoS)."""
        return self.fluid.fluid_model

    @property
    def fluid_properties(self) -> FluidProperties:
        """Get the fluid properties."""
        return self.fluid.properties

    @property
    def composition(self) -> FluidComposition:
        """Get the molar composition of the fluid."""
        return self.fluid.composition

    @property
    def conditions(self) -> ProcessConditions:
        """Get the process conditions (pressure and temperature)."""
        return self.fluid.properties.conditions

    @property
    def temperature_kelvin(self) -> float:
        """Get stream temperature [K]."""
        return self.fluid.temperature_kelvin

    @property
    def pressure_bara(self) -> float:
        """Get stream pressure [bara]."""
        return self.fluid.pressure_bara

    @property
    def density(self) -> float:
        """Get density [kg/m3]."""
        return self.fluid.density

    @property
    def molar_mass(self) -> float:
        """Get molar mass of the fluid [kg/mol]."""
        return self.fluid.molar_mass

    @property
    def standard_density_gas_phase_after_flash(self) -> float:
        """Get gas phase density at standard conditions [kg/Sm3]."""
        return self.fluid.standard_density_gas_phase_after_flash

    @property
    def enthalpy_joule_per_kg(self) -> float:
        """Get specific enthalpy [J/kg]."""
        return self.fluid.enthalpy_joule_per_kg

    @property
    def z(self) -> float:
        """Get compressibility factor [-]."""
        return self.fluid.z

    @property
    def kappa(self) -> float:
        """Get isentropic exponent [-]."""
        return self.fluid.kappa

    @property
    def vapor_fraction_molar(self) -> float:
        """Get molar vapor fraction [0-1]."""
        return self.fluid.vapor_fraction_molar

    @cached_property
    def volumetric_rate_m3_per_hour(self) -> float:
        """Calculate actual volumetric flow rate [m3/h]."""
        return self.mass_rate_kg_per_h / self.density

    @cached_property
    def standard_rate_sm3_per_day(self) -> float:
        """Calculate standard volumetric flow rate [Sm3/day]."""
        return self.mass_rate_kg_per_h / self.standard_density_gas_phase_after_flash * UnitConstants.HOURS_PER_DAY

    def with_mass_rate(self, mass_rate_kg_per_h: float) -> FluidStream:
        """Create new stream with same fluid but different rate.

        Args:
            mass_rate_kg_per_h: New mass flow rate [kg/h]

        Returns:
            New FluidStream with updated rate
        """
        return FluidStream(fluid=self.fluid, mass_rate_kg_per_h=mass_rate_kg_per_h)

    def with_new_fluid(self, fluid: Fluid) -> FluidStream:
        """Create new stream with updated fluid but same mass rate.

        This is the primary method for updating stream state after flash operations.
        Use FluidService interface to perform the flash, then call this method.

        Args:
            fluid: New Fluid instance (typically from a flash operation)

        Returns:
            New FluidStream with updated fluid and preserved mass rate

        Example:
            # Flash to new conditions via service
            new_fluid = fluid_service.create_fluid(
                stream.fluid_model, new_pressure, new_temperature
            )
            new_stream = stream.with_new_fluid(new_fluid)
        """
        return FluidStream(fluid=fluid, mass_rate_kg_per_h=self.mass_rate_kg_per_h)

    @classmethod
    def from_standard_rate(
        cls, standard_rate_m3_per_day: float, fluid_model: FluidModel, fluid_properties: FluidProperties
    ) -> FluidStream:
        """Create a stream from standard volumetric flow rate.

        Args:
            standard_rate_m3_per_day: Volumetric flow rate at standard conditions [Sm3/day]
            fluid_model: The fluid model (composition + EoS)
            fluid_properties: The fluid properties at the desired state

        Returns:
            A new FluidStream instance with mass rate calculated from standard rate
        """
        fluid = Fluid(fluid_model=fluid_model, properties=fluid_properties)
        mass_rate_kg_per_h = (
            standard_rate_m3_per_day * fluid.standard_density_gas_phase_after_flash / UnitConstants.HOURS_PER_DAY
        )
        return cls(fluid=fluid, mass_rate_kg_per_h=mass_rate_kg_per_h)
