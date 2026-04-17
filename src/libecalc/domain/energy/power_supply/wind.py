from libecalc.domain.energy.power_supply.power_supply import PowerSupply, PowerSupplyResult


class WindSupply(PowerSupply):
    def __init__(self, available_power_mw: float):
        self._available_power_mw = available_power_mw

    def evaluate(self, power_demand_mw: float) -> PowerSupplyResult:
        return PowerSupplyResult(
            fuel_rate_sm3_per_day=0.0,
            power_capacity_margin_mw=self._available_power_mw - power_demand_mw,
        )
