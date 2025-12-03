from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from libecalc.common.units import UnitConstants
from libecalc.domain.process.value_objects.fluid_stream.exceptions import NegativeMassRateException
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidComposition, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties
from libecalc.domain.process.value_objects.fluid_stream.process_conditions import ProcessConditions


@dataclass(frozen=True)
class FluidStream:
    """Represents a fluid stream with thermodynamic properties and a flow rate.

    This is a pure dataclass containing all computed properties - no JVM references.
    Flash operations delegate to NeqSimFluidService.

    Attributes:
        fluid_model: FluidModel containing composition and EoS model
        fluid_properties: FluidProperties containing all thermodynamic state data
        mass_rate_kg_per_h: Mass flow rate [kg/h]

    Example usage:
        # Create stream from fluid
        stream = fluid.to_stream(mass_rate_kg_per_h=1000)

        # Flash to new conditions (returns new stream with same rate)
        new_stream = stream.flash_pt(new_pressure, new_temperature)

        # Apply enthalpy change
        outlet_stream = inlet_stream.flash_ph(outlet_pressure, enthalpy_change)

        # Change rate only
        modified_stream = stream.with_mass_rate(new_rate)
    """

    fluid_model: FluidModel
    fluid_properties: FluidProperties
    mass_rate_kg_per_h: float

    def __post_init__(self):
        """Validate stream properties"""
        if self.mass_rate_kg_per_h < 0:
            raise NegativeMassRateException(self.mass_rate_kg_per_h)

    # =========================================================================
    # Convenience properties delegating to fluid_model or fluid_properties
    # =========================================================================

    @property
    def composition(self) -> FluidComposition:
        """Get the molar composition of the fluid."""
        return self.fluid_model.composition

    @property
    def conditions(self) -> ProcessConditions:
        """Get the process conditions (pressure and temperature)."""
        return self.fluid_properties.conditions

    @property
    def temperature_kelvin(self) -> float:
        """Get stream temperature [K]."""
        return self.fluid_properties.temperature_kelvin

    @property
    def pressure_bara(self) -> float:
        """Get stream pressure [bara]."""
        return self.fluid_properties.pressure_bara

    @property
    def density(self) -> float:
        """Get density [kg/m3]."""
        return self.fluid_properties.density

    @property
    def molar_mass(self) -> float:
        """Get molar mass of the fluid [kg/mol]."""
        return self.fluid_properties.molar_mass

    @property
    def standard_density(self) -> float:
        """Get gas phase density at standard conditions [kg/Sm3]."""
        return self.fluid_properties.standard_density

    @property
    def enthalpy_joule_per_kg(self) -> float:
        """Get specific enthalpy [J/kg]."""
        return self.fluid_properties.enthalpy_joule_per_kg

    @property
    def z(self) -> float:
        """Get compressibility factor [-]."""
        return self.fluid_properties.z

    @property
    def kappa(self) -> float:
        """Get isentropic exponent [-]."""
        return self.fluid_properties.kappa

    @property
    def vapor_fraction_molar(self) -> float:
        """Get molar vapor fraction [0-1]."""
        return self.fluid_properties.vapor_fraction_molar

    @cached_property
    def volumetric_rate(self) -> float:
        """Calculate volumetric flow rate [m3/h]."""
        return self.mass_rate_kg_per_h / self.density

    @cached_property
    def standard_rate(self) -> float:
        """Calculate standard volumetric flow rate [Sm3/day]."""
        return self.mass_rate_kg_per_h / self.standard_density * UnitConstants.HOURS_PER_DAY

    # =========================================================================
    # Rate modification
    # =========================================================================

    def with_mass_rate(self, mass_rate_kg_per_h: float) -> FluidStream:
        """Create new stream with same properties but different rate.

        Args:
            mass_rate_kg_per_h: New mass flow rate [kg/h]

        Returns:
            New FluidStream with updated rate
        """
        return FluidStream(
            fluid_model=self.fluid_model,
            fluid_properties=self.fluid_properties,
            mass_rate_kg_per_h=mass_rate_kg_per_h,
        )

    # =========================================================================
    # Flash convenience methods - delegate to NeqSimFluidService
    # =========================================================================

    def flash_pt(
        self,
        pressure_bara: float,
        temperature_kelvin: float,
        remove_liquid: bool = False,
    ) -> FluidStream:
        """TP flash - returns new stream at given conditions, same rate.

        Args:
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            New FluidStream at the target conditions with same mass rate
        """
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        new_props = NeqSimFluidService.instance().get_properties(
            fluid_model=self.fluid_model,
            pressure_bara=pressure_bara,
            temperature_kelvin=temperature_kelvin,
            remove_liquid=remove_liquid,
        )
        return FluidStream(
            fluid_model=self.fluid_model,
            fluid_properties=new_props,
            mass_rate_kg_per_h=self.mass_rate_kg_per_h,
        )

    def flash_ph(
        self,
        pressure_bara: float,
        enthalpy_change_joule_per_kg: float,
        remove_liquid: bool = False,
    ) -> FluidStream:
        """PH flash - returns new stream with enthalpy change applied, same rate.

        Args:
            pressure_bara: Target pressure in bara
            enthalpy_change_joule_per_kg: Change in specific enthalpy [J/kg]
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            New FluidStream at the resulting conditions with same mass rate
        """
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        target_enthalpy = self.fluid_properties.enthalpy_joule_per_kg + enthalpy_change_joule_per_kg
        new_props = NeqSimFluidService.instance().flash_ph(
            fluid_model=self.fluid_model,
            pressure_bara=pressure_bara,
            target_enthalpy=target_enthalpy,
            remove_liquid=remove_liquid,
        )
        return FluidStream(
            fluid_model=self.fluid_model,
            fluid_properties=new_props,
            mass_rate_kg_per_h=self.mass_rate_kg_per_h,
        )

    # =========================================================================
    # Class methods for stream creation
    # =========================================================================

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
        standard_density = fluid_properties.standard_density
        mass_rate_kg_per_h = standard_rate_m3_per_day * standard_density / UnitConstants.HOURS_PER_DAY

        return cls(fluid_model=fluid_model, fluid_properties=fluid_properties, mass_rate_kg_per_h=mass_rate_kg_per_h)

    # =========================================================================
    # Backwards compatibility - will be deprecated
    # =========================================================================

    @property
    def properties(self) -> FluidProperties:
        """DEPRECATED: Use fluid_properties instead."""
        return self.fluid_properties

    @property
    def standard_density_gas_phase_after_flash(self) -> float:
        """DEPRECATED: Use standard_density instead."""
        return self.fluid_properties.standard_density

    @property
    def enthalpy(self) -> float:
        """DEPRECATED: Use enthalpy_joule_per_kg instead."""
        return self.fluid_properties.enthalpy_joule_per_kg

    def create_stream_with_new_conditions(
        self, conditions: ProcessConditions, remove_liquid: bool = False
    ) -> FluidStream:
        """DEPRECATED: Use flash_pt() instead.

        Create a new stream with modified conditions via TP-flash.

        Args:
            conditions: New process conditions (pressure and temperature)
            remove_liquid: Whether to remove liquid phase after flash calculation

        Returns:
            A new FluidStream instance with the modified conditions
        """
        return self.flash_pt(
            pressure_bara=conditions.pressure_bara,
            temperature_kelvin=conditions.temperature_kelvin,
            remove_liquid=remove_liquid,
        )

    def create_stream_with_new_pressure_and_enthalpy_change(
        self, pressure_bara: float, enthalpy_change_joule_per_kg: float, remove_liquid: bool = False
    ) -> FluidStream:
        """DEPRECATED: Use flash_ph() instead.

        Create a new stream with modified pressure and changed enthalpy via PH-flash.

        Args:
            pressure_bara: Target pressure [bara]
            enthalpy_change_joule_per_kg: Change in specific enthalpy [J/kg]
            remove_liquid: Whether to remove liquid phase after flash calculation

        Returns:
            A new FluidStream instance with the modified pressure and resulting temperature
        """
        return self.flash_ph(
            pressure_bara=pressure_bara,
            enthalpy_change_joule_per_kg=enthalpy_change_joule_per_kg,
            remove_liquid=remove_liquid,
        )
