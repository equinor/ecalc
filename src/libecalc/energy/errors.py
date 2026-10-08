from __future__ import annotations

from libecalc.common.errors.exceptions import EcalcError


class EnergyDomainError(EcalcError):
    """Base for all energy domain errors."""

    def __init__(self, message: str):
        super().__init__(title="Energy domain error", message=message)


class NegativeEnergyError(EnergyDomainError):
    """Raised when a demand value is negative."""

    def __init__(self, value: float, energy_type: str):
        self.value = value
        self.energy_type = energy_type
        super().__init__(f"{energy_type} value must be non-negative, got {value}")


class NonFiniteEnergyError(EnergyDomainError):
    """Raised when an energy value is NaN or infinite."""

    def __init__(self, value: float, energy_type: str):
        self.value = value
        self.energy_type = energy_type
        super().__init__(f"{energy_type} value must be finite, got {value}")


class InvalidCapacityTypeError(EnergyDomainError):
    """Raised when a unit's capacity is of another energy type than the unit delivers."""

    def __init__(self, unit_name: str, expected: str, actual: str):
        super().__init__(f"Capacity for '{unit_name}' must be {expected}, got {actual}")


class InvalidEnergyNetworkError(EnergyDomainError):
    """Raised when an energy network violates a topology invariant."""


class InvalidDispatchError(EnergyDomainError):
    """Raised when a dispatch strategy is asked to allocate over candidates it cannot serve."""


class InvalidEnergyNetworkInputError(EnergyDomainError):
    """Raised when energy network evaluation input is invalid."""
