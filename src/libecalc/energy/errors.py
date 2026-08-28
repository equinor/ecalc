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


class InvalidEnergyNetworkError(EnergyDomainError):
    """Raised when an energy network violates a topology invariant."""
