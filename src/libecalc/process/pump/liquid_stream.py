"""A constant-density liquid stream defined by pressure, density and mass flow rate.

It carries no equation of state, composition, temperature or viscosity.
"""

from __future__ import annotations

import dataclasses

from libecalc.common.ddd import value_object
from libecalc.common.units import UnitConstants
from libecalc.process.pump.exceptions import (
    NegativeMassRateException,
    NonPositiveDensityException,
    NonPositivePressureException,
)


@value_object
class LiquidStream:
    """A liquid stream modelled with constant density.

    Attributes:
        pressure_bara: Stream pressure [bara].
        density_kg_per_m3: Liquid density [kg/m3].
        mass_rate_kg_per_h: Mass flow rate [kg/h].
    """

    pressure_bara: float
    density_kg_per_m3: float
    mass_rate_kg_per_h: float

    def __post_init__(self):
        if self.density_kg_per_m3 <= 0:
            raise NonPositiveDensityException(self.density_kg_per_m3)
        if self.mass_rate_kg_per_h < 0:
            raise NegativeMassRateException(self.mass_rate_kg_per_h)
        if self.pressure_bara <= 0:
            raise NonPositivePressureException(self.pressure_bara)

    @property
    def volumetric_rate_m3_per_hour(self) -> float:
        """Volumetric flow rate [m3/h]"""
        return self.mass_rate_kg_per_h / self.density_kg_per_m3

    @property
    def volumetric_rate_m3_per_day(self) -> float:
        """Volumetric flow rate [m3/day]"""
        return self.volumetric_rate_m3_per_hour * UnitConstants.HOURS_PER_DAY

    def with_mass_rate(self, mass_rate_kg_per_h: float) -> LiquidStream:
        """Return a new stream with the same state but a different mass rate."""
        return dataclasses.replace(self, mass_rate_kg_per_h=mass_rate_kg_per_h)

    def with_pressure(self, pressure_bara: float) -> LiquidStream:
        """Return a new stream at a different pressure while keeping density unchanged."""
        return dataclasses.replace(self, pressure_bara=pressure_bara)

    @classmethod
    def from_volumetric_rate(
        cls,
        volumetric_rate_m3_per_day: float,
        pressure_bara: float,
        density_kg_per_m3: float,
    ) -> LiquidStream:
        """Create a stream from an actual volumetric flow rate [m3/day]."""
        mass_rate_kg_per_h = volumetric_rate_m3_per_day * density_kg_per_m3 / UnitConstants.HOURS_PER_DAY
        return cls(
            pressure_bara=pressure_bara,
            density_kg_per_m3=density_kg_per_m3,
            mass_rate_kg_per_h=mass_rate_kg_per_h,
        )
