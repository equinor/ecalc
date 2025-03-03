from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessConditions:
    """
    Represents the physical conditions of a process stream.

    Attributes:
        temperature: Temperature in Kelvin
        pressure: Pressure in bara (absolute bar)
    """

    temperature: float
    pressure: float

    def __post_init__(self):
        """Validate conditions"""
        if self.temperature <= 0:
            raise ValueError(f"Temperature must be positive, got {self.temperature}")
        if self.pressure <= 0:
            raise ValueError(f"Pressure must be positive, got {self.pressure}")

    @property
    def temperature_celsius(self) -> float:
        """Get temperature in Celsius."""
        return self.temperature - 273.15

    @property
    def pressure_pascal(self) -> float:
        """Get pressure in Pascal."""
        return self.pressure * 1e5

    @property
    def pressure_atm(self) -> float:
        """Get pressure in atmospheres."""
        return self.pressure / 1.01325

    @classmethod
    def from_celsius(cls, temperature_celsius: float, pressure: float) -> ProcessConditions:
        """Create instance with temperature specified in Celsius."""
        return cls(temperature=temperature_celsius + 273.15, pressure=pressure)
