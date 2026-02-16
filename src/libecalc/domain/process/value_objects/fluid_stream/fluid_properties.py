from __future__ import annotations

from dataclasses import dataclass

from libecalc.domain.process.value_objects.fluid_stream.process_conditions import ProcessConditions


@dataclass(frozen=True)
class FluidProperties:
    """All thermodynamic properties at a given state - pure data, no JVM references.

    This dataclass contains all computed thermodynamic properties extracted from
    a flash calculation. It serves as an immutable snapshot of fluid state.

    Note: composition and eos_model are NOT stored here - they belong to FluidModel
    which is stored separately on FluidStream.

    Attributes:
        temperature_kelvin: Temperature in Kelvin
        pressure_bara: Pressure in bara (absolute bar)
        density: Density in kg/m³
        enthalpy_joule_per_kg: Specific enthalpy in J/kg
        z: Compressibility factor (dimensionless)
        kappa: Isentropic exponent (Cp/Cv ratio)
        vapor_fraction_molar: Molar vapor fraction (0-1)
        molar_mass: Molar mass in kg/mol (from composition, not NeqSim)
        standard_density: Gas-phase density at standard conditions in kg/Sm³
    """

    temperature_kelvin: float
    pressure_bara: float
    density: float
    enthalpy_joule_per_kg: float
    z: float
    kappa: float
    vapor_fraction_molar: float
    molar_mass: float
    standard_density: float

    @property
    def conditions(self) -> ProcessConditions:
        """Get process conditions (pressure and temperature)."""
        return ProcessConditions(
            pressure_bara=self.pressure_bara,
            temperature_kelvin=self.temperature_kelvin,
        )

    def __repr__(self) -> str:
        return (
            f"FluidProperties(temperature_kelvin={self.temperature_kelvin}, "
            f"pressure_bara={self.pressure_bara}, density={self.density}, "
            f"enthalpy_joule_per_kg={self.enthalpy_joule_per_kg}, z={self.z}, "
            f"kappa={self.kappa}, vapor_fraction_molar={self.vapor_fraction_molar}, "
            f"molar_mass={self.molar_mass}, standard_density={self.standard_density})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def __sub__(self, other: FluidProperties) -> DeltaFluidProperties:
        if not isinstance(other, FluidProperties):
            raise TypeError(f"Unsupported operand type(s) for -: 'FluidProperties' and '{type(other).__name__}'")

        return DeltaFluidProperties(
            temperature_kelvin=self.temperature_kelvin - other.temperature_kelvin,
            pressure_bara=self.pressure_bara - other.pressure_bara,
            density=self.density - other.density,
            enthalpy_joule_per_kg=self.enthalpy_joule_per_kg - other.enthalpy_joule_per_kg,
            z=self.z - other.z,
            kappa=self.kappa - other.kappa,
            vapor_fraction_molar=self.vapor_fraction_molar - other.vapor_fraction_molar,
            molar_mass=self.molar_mass - other.molar_mass,
            standard_density=self.standard_density - other.standard_density,
        )


@dataclass(frozen=True)
class DeltaFluidProperties(FluidProperties):
    """Represents the change in fluid properties (T/P), calculated as outlet - inlet."""

    def __repr__(self) -> str:
        temperature_kelvin = f"temperature_kelvin: {self.temperature_kelvin}" if self.temperature_kelvin != 0.0 else ""
        pressure_bara = f"pressure_bara: {self.pressure_bara}" if self.pressure_bara != 0.0 else ""
        density = f"density: {self.density}" if self.density != 0.0 else ""
        enthalpy_joule_per_kg = (
            f"enthalpy_joule_per_kg: {self.enthalpy_joule_per_kg}" if self.enthalpy_joule_per_kg != 0.0 else ""
        )
        z = f"z: {self.z}" if self.z != 0.0 else ""
        kappa = f"kappa: {self.kappa}" if self.kappa != 0.0 else ""
        vapor_fraction_molar = (
            f"vapor_fraction_molar: {self.vapor_fraction_molar}" if self.vapor_fraction_molar != 0.0 else ""
        )
        molar_mass = f"molar_mass: {self.molar_mass}" if self.molar_mass != 0.0 else ""
        standard_density = f"standard_density: {self.standard_density}" if self.standard_density != 0.0 else ""

        change_string = ", ".join(
            filter(
                None,
                [
                    temperature_kelvin,
                    pressure_bara,
                    density,
                    enthalpy_joule_per_kg,
                    z,
                    kappa,
                    vapor_fraction_molar,
                    molar_mass,
                    standard_density,
                ],
            )
        )

        return "" if not change_string else f"DeltaFluidProperties({change_string})"
