from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from libecalc.common.units import UnitConstants
from libecalc.domain.process.value_objects.fluid_stream.exceptions import NegativeMassRateException
from libecalc.domain.process.value_objects.fluid_stream.process_conditions import ProcessConditions
from libecalc.domain.process.value_objects.fluid_stream.thermo_system import ThermoSystemInterface


@dataclass(frozen=True)
class FluidStream:
    """
    Represents a fluid stream with a thermodynamic state and a flow rate.

    Attributes:
        thermo_system: ThermoSystemInterface representing the fluid's thermodynamic state
        mass_rate: Mass flow rate [kg/h]
    """

    thermo_system: ThermoSystemInterface
    mass_rate_kg_per_h: float

    def __post_init__(self):
        """Validate stream properties"""
        if self.mass_rate_kg_per_h < 0:
            raise NegativeMassRateException(self.mass_rate_kg_per_h)

    @property
    def conditions(self) -> ProcessConditions:
        """Get the process conditions (pressure and temperature)."""
        return self.thermo_system.conditions

    @property
    def temperature_kelvin(self) -> float:
        """Get stream temperature [K]."""
        return self.thermo_system.temperature_kelvin

    @property
    def pressure_bara(self) -> float:
        """Get stream pressure [bara]."""
        return self.thermo_system.pressure_bara

    @property
    def density(self) -> float:
        """Get density [kg/m³]."""
        return self.thermo_system.density

    @property
    def molar_mass(self) -> float:
        """Get molar mass of the fluid [kg/mol]."""
        return self.thermo_system.molar_mass

    @property
    def standard_density_gas_phase_after_flash(self) -> float:
        """Get gas phase density at standard conditions after TP flash and liquid removal [kg/Sm³]."""
        return self.thermo_system.standard_density_gas_phase_after_flash

    @property
    def enthalpy(self) -> float:
        """Get specific enthalpy [J/kg]."""
        return self.thermo_system.enthalpy

    @property
    def z(self) -> float:
        """Get compressibility factor [-]."""
        return self.thermo_system.z

    @property
    def kappa(self) -> float:
        """Get isentropic exponent [-]."""
        return self.thermo_system.kappa

    @property
    def vapor_fraction_molar(self) -> float:
        """Get molar vapor fraction [0-1]."""
        return self.thermo_system.vapor_fraction_molar

    @cached_property
    def volumetric_rate(self) -> float:
        """Calculate volumetric flow rate [m³/h]."""
        return self.mass_rate_kg_per_h / self.density

    @cached_property
    def standard_rate(self) -> float:
        """Calculate standard volumetric flow rate [Sm³/day]."""
        return self.mass_rate_kg_per_h / self.standard_density_gas_phase_after_flash * UnitConstants.HOURS_PER_DAY

    def create_stream_with_new_conditions(
        self, conditions: ProcessConditions, remove_liquid: bool = False
    ) -> FluidStream:
        """Create a new stream with modified conditions.
        This performs a PT-flash on the fluid.

        Args:
            conditions: New process conditions (pressure and temperature)
            remove_liquid: Whether to remove liquid phase after flash calculation
            # Note: remove liquid only clones the gas phase in the current neqsim wrapper implementation, and does not alter flow rate

        Returns:
            A new Stream instance with the modified conditions
        """
        new_state = self.thermo_system.flash_to_conditions(
            conditions=conditions,
            remove_liquid=remove_liquid,
        )
        return FluidStream(
            thermo_system=new_state,
            mass_rate_kg_per_h=self.mass_rate_kg_per_h,
        )

    def create_stream_with_new_pressure_and_enthalpy_change(
        self, pressure_bara: float, enthalpy_change_joule_per_kg: float, remove_liquid: bool = False
    ) -> FluidStream:
        """Create a new stream with modified pressure and changed enthalpy.
        This performs a PH-flash on the fluid.

        Args:
            pressure_bara: Target pressure [bara]
            enthalpy_change: Change in specific enthalpy [J/kg]
            remove_liquid: Whether to remove liquid phase after flash calculation
            # Note: remove liquid only clones the gas phase in the current neqsim wrapper implementation, and does not alter flow rate

        Returns:
            A new Stream instance with the modified pressure and resulting temperature
        """
        new_state = self.thermo_system.flash_to_pressure_and_enthalpy_change(
            pressure_bara=pressure_bara,
            enthalpy_change=enthalpy_change_joule_per_kg,
            remove_liquid=remove_liquid,
        )

        return FluidStream(
            thermo_system=new_state,
            mass_rate_kg_per_h=self.mass_rate_kg_per_h,
        )

    @classmethod
    def from_standard_rate(cls, standard_rate_m3_per_day: float, thermo_system: ThermoSystemInterface) -> FluidStream:
        """Create a stream from standard volumetric flow rate.

        This allows creating a stream based on standard volumetric flow rate instead of mass rate.
        (Note: We use standard density of the gas phase after flash at standard conditions.
        It does not make sense to use standard density of the system if it contains liquid phase.)

        Args:
            standard_rate: Volumetric flow rate at standard conditions [Sm³/day]
            thermo_system: The thermo system representing the fluid state

        Returns:
            A new Stream instance with mass rate calculated from standard rate
        """
        # Calculate mass rate from standard rate
        standard_density = thermo_system.standard_density_gas_phase_after_flash
        mass_rate_kg_per_h = standard_rate_m3_per_day * standard_density / UnitConstants.HOURS_PER_DAY

        return cls(thermo_system=thermo_system, mass_rate_kg_per_h=mass_rate_kg_per_h)
