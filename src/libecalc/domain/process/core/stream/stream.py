from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from libecalc.common.units import UnitConstants
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.exceptions import NegativeMassRateException
from libecalc.domain.process.core.stream.thermo_system import ThermoSystemInterface


@dataclass(frozen=True)
class Stream:
    """
    Represents a fluid stream with a thermodynamic state and a flow rate.

    Attributes:
        thermo_system: ThermoSystemInterface representing the fluid's thermodynamic state
        mass_rate: Mass flow rate [kg/h]
    """

    thermo_system: ThermoSystemInterface
    mass_rate: float

    def __post_init__(self):
        """Validate stream properties"""
        if self.mass_rate < 0:
            raise NegativeMassRateException(self.mass_rate)

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
        """Calculate volumetric flow rate [m³/s]."""
        return self.mass_rate / self.density

    @cached_property
    def standard_rate(self) -> float:
        """Calculate standard volumetric flow rate [Sm³/day]."""
        return self.mass_rate / self.standard_density_gas_phase_after_flash * UnitConstants.HOURS_PER_DAY

    def create_stream_with_new_conditions(self, conditions: ProcessConditions, remove_liquid: bool = True) -> Stream:
        """Create a new stream with modified conditions.

        Args:
            conditions: New process conditions (pressure and temperature)
            remove_liquid: Whether to remove liquid phase after flash calculation

        Returns:
            A new Stream instance with the modified conditions
        """
        new_state = self.thermo_system.flash_to_conditions(
            conditions=conditions,
            remove_liquid=remove_liquid,
        )
        return Stream(
            thermo_system=new_state,
            mass_rate=self.mass_rate,
        )

    def create_stream_with_new_pressure_and_enthalpy_change(
        self, pressure_bara: float, enthalpy_change: float, remove_liquid: bool = True
    ) -> Stream:
        """Create a new stream with modified pressure and changed enthalpy.
        This simulates a PH-flash operation.

        Args:
            pressure_bara: Target pressure [bara]
            enthalpy_change: Change in specific enthalpy [J/kg]
            remove_liquid: Whether to remove liquid phase after flash calculation

        Returns:
            A new Stream instance with the modified pressure and resulting temperature
        """
        new_state = self.thermo_system.flash_to_pressure_and_enthalpy_change(
            pressure_bara=pressure_bara,
            enthalpy_change=enthalpy_change,
            remove_liquid=remove_liquid,
        )

        return Stream(
            thermo_system=new_state,
            mass_rate=self.mass_rate,
        )

    @classmethod
    def from_standard_rate(cls, standard_rate: float, thermo_system: ThermoSystemInterface) -> Stream:
        """Create a stream from standard volumetric flow rate.

        This allows creating a stream based on standard volumetric flow rate instead of mass rate.

        Args:
            standard_rate: Volumetric flow rate at standard conditions [Sm³/day]
            thermo_system: The thermo system representing the fluid state

        Returns:
            A new Stream instance with mass rate calculated from standard rate
        """
        # Calculate mass rate from standard rate
        standard_density = thermo_system.standard_density_gas_phase_after_flash
        mass_rate = standard_rate * standard_density / UnitConstants.HOURS_PER_DAY

        return cls(thermo_system=thermo_system, mass_rate=mass_rate)
