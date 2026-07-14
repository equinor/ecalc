"""Exceptions for invalid liquid streams and pump configuration."""

from libecalc.common.errors.exceptions import EcalcError


class InvalidLiquidStreamException(EcalcError):
    def __init__(self, title: str | None = None, reason: str | None = None):
        super().__init__(title=f"Invalid liquid stream: {title or ''}", message=reason or "")


class NonPositiveDensityException(InvalidLiquidStreamException):
    """Raised when a liquid density is not strictly positive."""

    def __init__(self, density_kg_per_m3: float):
        self.density_kg_per_m3 = density_kg_per_m3
        super().__init__(reason="Liquid density must be positive.")


class NegativeMassRateException(InvalidLiquidStreamException):
    """Raised when a liquid stream mass rate is negative."""

    def __init__(self, mass_rate_kg_per_h: float):
        self.mass_rate_kg_per_h = mass_rate_kg_per_h
        super().__init__(reason="Mass rate cannot be negative.")


class NonPositivePressureException(InvalidLiquidStreamException):
    """Raised when a liquid pressure is not strictly positive."""

    def __init__(self, pressure_bara: float):
        self.pressure_bara = pressure_bara
        super().__init__(reason="Pressure must be positive.")
