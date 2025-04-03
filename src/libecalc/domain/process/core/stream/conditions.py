from __future__ import annotations

from dataclasses import dataclass

from libecalc.common.units import Unit, UnitConstants
from libecalc.domain.process.core.stream.exceptions import NonPositivePressureException, NonPositiveTemperatureException


@dataclass(frozen=True)
class ProcessConditions:
    """
    Represents the physical conditions of a process stream.

    Attributes:
        temperature: Temperature in Kelvin
        pressure: Pressure in bara (absolute bar)
    """

    temperature_kelvin: float
    pressure_bara: float

    def __post_init__(self):
        """Validate conditions"""
        if self.temperature_kelvin <= 0:
            raise NonPositiveTemperatureException(self.temperature_kelvin)
        if self.pressure_bara <= 0:
            raise NonPositivePressureException(self.pressure_bara)

    @property
    def temperature_celsius(self) -> float:
        """Get temperature in Celsius."""
        return Unit.KELVIN.to(Unit.CELSIUS)(self.temperature_kelvin)

    @property
    def pressure_pascal(self) -> float:
        """Get pressure in Pascal."""
        return Unit.BARA.to(Unit.PASCAL)(self.pressure_bara)

    @property
    def pressure_atm(self) -> float:
        """Get pressure in atmospheres."""
        return self.pressure_bara / UnitConstants.STANDARD_PRESSURE_BARA

    @classmethod
    def from_celsius(cls, temperature_celsius: float, pressure_bara: float) -> ProcessConditions:
        """Create instance with temperature specified in Celsius."""
        return cls(temperature_kelvin=Unit.CELSIUS.to(Unit.KELVIN)(temperature_celsius), pressure_bara=pressure_bara)

    @classmethod
    def standard_conditions(cls) -> ProcessConditions:
        """Create instance with standard conditions."""
        return cls(
            temperature_kelvin=UnitConstants.STANDARD_TEMPERATURE_KELVIN,
            pressure_bara=UnitConstants.STANDARD_PRESSURE_BARA,
        )
