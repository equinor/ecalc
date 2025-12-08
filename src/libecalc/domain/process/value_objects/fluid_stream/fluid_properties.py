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
