from libecalc.domain.energy.infrastructure_contracts import FuelConverter


class SimpleFuelConverter(FuelConverter):
    """Test stub: linear fuel consumption.

    fuel_per_mw: Sm³/day per MW (e.g. 100 means 1 MW costs 100 Sm³/day)
    """

    def __init__(self, fuel_per_mw: float, max_power_mw: float = float("inf")):
        self._fuel_per_mw = fuel_per_mw
        self._max_power_mw = max_power_mw

    def evaluate_fuel_usage(self, power_mw: float) -> float:
        return power_mw * self._fuel_per_mw

    def evaluate_power_capacity_margin(self, power_mw: float) -> float:
        return self._max_power_mw - power_mw
