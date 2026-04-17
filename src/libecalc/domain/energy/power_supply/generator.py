from libecalc.domain.energy.infrastructure_contracts import FuelConverter
from libecalc.domain.energy.power_supply.power_supply import PowerSupply, PowerSupplyResult


class GeneratorSupply(PowerSupply):
    def __init__(self, generator: FuelConverter):
        self._generator = generator

    def evaluate(self, power_demand_mw: float) -> PowerSupplyResult:
        return PowerSupplyResult(
            fuel_rate_sm3_per_day=self._generator.evaluate_fuel_usage(power_demand_mw),
            power_capacity_margin_mw=self._generator.evaluate_power_capacity_margin(power_demand_mw),
        )
