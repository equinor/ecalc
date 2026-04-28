from __future__ import annotations

from dataclasses import dataclass

from libecalc.common.units import UnitConstants


@dataclass(frozen=True)
class LiquidStream:
    """A fully-specified incompressible liquid stream.

    Density is constant (incompressible assumption) — no thermodynamic flash needed.
    Used as the inlet/outlet type for LiquidProcessUnit (e.g. Pump).
    """

    pressure_bara: float
    density_kg_per_m3: float
    mass_rate_kg_per_h: float

    def __post_init__(self) -> None:
        if self.density_kg_per_m3 <= 0:
            raise ValueError(f"Density must be positive, got {self.density_kg_per_m3}")
        if self.mass_rate_kg_per_h < 0:
            raise ValueError(f"Mass rate cannot be negative, got {self.mass_rate_kg_per_h}")

    @property
    def volumetric_rate_m3_per_hour(self) -> float:
        return self.mass_rate_kg_per_h / self.density_kg_per_m3

    @property
    def standard_density(self) -> float:
        """Liquid density [kg/m³].

        For incompressible liquids, operating density ≈ standard density
        (no significant pressure/temperature correction needed).
        """
        return self.density_kg_per_m3

    @property
    def standard_rate_sm3_per_day(self) -> float:
        """Volumetric flow rate [Sm³/day].

        For incompressible liquids, standard ≈ actual volume, so this is
        equivalent to actual m³/day. Matches the FluidStream interface so
        both stream types work with the same RecirculationLoop logic.
        """
        return self.mass_rate_kg_per_h * UnitConstants.HOURS_PER_DAY / self.density_kg_per_m3

    def with_pressure(self, pressure_bara: float) -> LiquidStream:
        return LiquidStream(
            pressure_bara=pressure_bara,
            density_kg_per_m3=self.density_kg_per_m3,
            mass_rate_kg_per_h=self.mass_rate_kg_per_h,
        )

    def with_mass_rate(self, mass_rate_kg_per_h: float) -> LiquidStream:
        return LiquidStream(
            pressure_bara=self.pressure_bara,
            density_kg_per_m3=self.density_kg_per_m3,
            mass_rate_kg_per_h=mass_rate_kg_per_h,
        )
