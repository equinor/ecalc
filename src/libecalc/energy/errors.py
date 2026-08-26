from libecalc.common.errors.exceptions import EcalcError


class EnergyDomainError(EcalcError):
    """Base for all energy domain errors."""

    def __init__(self, message: str):
        super().__init__(title="Energy domain error", message=message)


class NegativeDemandError(EnergyDomainError):
    """Raised when a demand value is negative."""

    def __init__(self, value: float, demand_type: str):
        self.value = value
        self.demand_type = demand_type
        super().__init__(f"{demand_type} value must be non-negative, got {value}")
