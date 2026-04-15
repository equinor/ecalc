from libecalc.domain.energy.power_supply.power_supply import PowerSupply, PowerSupplyResult
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_model import GeneratorSetModel


class GeneratorSetSupply(PowerSupply):
    def __init__(self, generator_set: GeneratorSetModel):
        self._generator_set = generator_set

    def evaluate(self, power_demand_mw: float) -> PowerSupplyResult:
        return PowerSupplyResult(
            fuel_rate_sm3_per_day=self._generator_set.evaluate_fuel_usage(power_demand_mw),
            power_capacity_margin_mw=self._generator_set.evaluate_power_capacity_margin(power_demand_mw),
        )
