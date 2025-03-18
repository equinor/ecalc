from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from libecalc.common.units import UnitConstants
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.exceptions import NegativeMassRateException
from libecalc.domain.process.core.stream.fluid import Fluid


@dataclass(frozen=True)
class Stream:
    """
    Represents a fluid stream with its properties and conditions.

    This class consolidates the functionality from various existing stream
    implementations in the system.

    Attributes:
        fluid: Fluid object containing composition and EoS model
        conditions: Process conditions (temperature and pressure)
        mass_rate: Mass flow rate [kg/h]
    """

    fluid: Fluid
    conditions: ProcessConditions
    mass_rate: float

    def __post_init__(self):
        """Validate stream properties"""
        if self.mass_rate < 0:
            raise NegativeMassRateException(self.mass_rate)

    @property
    def temperature(self) -> float:
        """Get stream temperature [K]."""
        return self.conditions.temperature_kelvin

    @property
    def pressure(self) -> float:
        """Get stream pressure [bara]."""
        return self.conditions.pressure_bara

    @cached_property
    def density(self) -> float:
        """Get density [kg/m³]."""
        return self.fluid._thermodynamic_engine.get_density(
            self.fluid, pressure=self.pressure, temperature=self.temperature
        )

    @cached_property
    def molar_mass(self) -> float:
        """Get molar mass of the fluid [kg/kmol]."""
        return self.fluid._thermodynamic_engine.get_molar_mass(self.fluid)

    @cached_property
    def standard_density_gas_phase_after_flash(self) -> float:
        """Get gas phase density at standard conditions after TP flash and liquid removal [kg/Sm³]."""
        return self.fluid._thermodynamic_engine.get_standard_density_gas_phase_after_flash(self.fluid)

    @cached_property
    def enthalpy(self) -> float:
        """Get specific enthalpy [J/kg]."""
        return self.fluid._thermodynamic_engine.get_enthalpy(
            self.fluid, pressure=self.pressure, temperature=self.temperature
        )

    @cached_property
    def z(self) -> float:
        """Get compressibility factor [-]."""
        return self.fluid._thermodynamic_engine.get_z(self.fluid, pressure=self.pressure, temperature=self.temperature)

    @cached_property
    def kappa(self) -> float:
        """Get isentropic exponent [-]."""
        return self.fluid._thermodynamic_engine.get_kappa(
            self.fluid, pressure=self.pressure, temperature=self.temperature
        )

    @cached_property
    def volumetric_rate(self) -> float:
        """Calculate volumetric flow rate [m³/s]."""
        return self.mass_rate / self.density

    @cached_property
    def standard_rate(self) -> float:
        """Calculate standard volumetric flow rate [Sm³/day]."""
        return self.mass_rate / self.standard_density_gas_phase_after_flash * UnitConstants.HOURS_PER_DAY

    def create_stream_with_new_conditions(self, new_conditions: ProcessConditions) -> Stream:
        """Create a new stream with modified conditions.

        Args:
            new_conditions: New process conditions to apply

        Returns:
            A new Stream instance with the modified conditions
        """
        return Stream(
            fluid=self.fluid,
            conditions=new_conditions,
            mass_rate=self.mass_rate,
        )

    def create_stream_with_new_pressure_and_temperature(self, new_pressure: float, new_temperature: float) -> Stream:
        """Create a new stream with modified pressure and temperature.

        Args:
            new_pressure: New pressure [bara]
            new_temperature: New temperature [K]

        Returns:
            A new Stream instance with the modified pressure and temperature
        """
        return self.create_stream_with_new_conditions(
            ProcessConditions(pressure_bara=new_pressure, temperature_kelvin=new_temperature)
        )

    def create_stream_with_new_pressure_and_enthalpy_change(
        self, new_pressure: float, enthalpy_change: float
    ) -> Stream:
        """Create a new stream with modified pressure and changed enthalpy.
        TODO: This is a temporary method with only the NeqSim backend.

        This simulates a PH-flash operation.

        Args:
            new_pressure: Target pressure [bara]
            enthalpy_change: Change in specific enthalpy [J/kg]

        Returns:
            A new Stream instance with the modified pressure and resulting temperature
        """
        from ecalc_neqsim_wrapper.thermo import NeqsimFluid

        neqsim_fluid = NeqsimFluid.create_thermo_system(
            composition=self.fluid.composition,
            temperature_kelvin=self.temperature,
            pressure_bara=self.pressure,
            eos_model=self.fluid.eos_model,
        )

        # Use NeqSim's PH flash to get the new state
        neqsim_fluid = neqsim_fluid.set_new_pressure_and_enthalpy(
            new_pressure=new_pressure,
            new_enthalpy_joule_per_kg=neqsim_fluid.enthalpy_joule_per_kg + enthalpy_change,
            remove_liquid=True,
        )

        # Return a new stream with the calculated temperature
        return self.create_stream_with_new_pressure_and_temperature(
            new_pressure=new_pressure, new_temperature=neqsim_fluid.temperature_kelvin
        )

    @classmethod
    def from_standard_rate(
        cls,
        fluid: Fluid,
        conditions: ProcessConditions,
        standard_rate: float,  # Sm³/day
    ) -> Stream:
        """Create a stream from standard volumetric flow rate instead of mass rate.

        Args:
            fluid: Fluid object containing composition and EoS model
            conditions: Process conditions (temperature and pressure)
            standard_rate: Volumetric flow rate at standard conditions [Sm³/day]

        Returns:
            A new Stream instance with mass rate calculated from standard rate
        """
        # Create a temporary fluid to get standard density
        standard_density = fluid._thermodynamic_engine.get_standard_density_gas_phase_after_flash(fluid)

        # Convert standard rate to mass rate
        mass_rate = standard_rate * standard_density / UnitConstants.HOURS_PER_DAY

        return cls(fluid=fluid, conditions=conditions, mass_rate=mass_rate)
