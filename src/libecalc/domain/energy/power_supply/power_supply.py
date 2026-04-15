from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PowerSupplyResult:
    fuel_rate_sm3_per_day: float
    power_capacity_margin_mw: float


class PowerSupply(ABC):
    @abstractmethod
    def evaluate(self, power_demand_mw: float) -> PowerSupplyResult: ...
