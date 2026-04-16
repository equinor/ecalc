from dataclasses import dataclass

from libecalc.domain.energy.power_supply.power_supply import PowerSupply, PowerSupplyResult


@dataclass
class ShoreConnectionResult(PowerSupplyResult):
    power_from_shore_mw: float


class ShoreSupply(PowerSupply):
    def __init__(
        self,
        max_capacity_mw: float,
        cable_loss_fraction: float = 0.0,
    ):
        self._max_capacity_mw = max_capacity_mw
        self._cable_loss_fraction = cable_loss_fraction

    def evaluate(self, power_demand_mw: float) -> ShoreConnectionResult:
        power_from_shore_mw = power_demand_mw * (1 + self._cable_loss_fraction)
        return ShoreConnectionResult(
            fuel_rate_sm3_per_day=0.0,
            power_capacity_margin_mw=self._max_capacity_mw - power_from_shore_mw,
            power_from_shore_mw=power_from_shore_mw,
        )
