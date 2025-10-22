from __future__ import annotations

import numpy as np

from libecalc.common.units import Unit
from libecalc.domain.process.core.results import EnergyFunctionResult


class TurbineResult(EnergyFunctionResult):
    def __init__(
        self,
        load: list[float],  # MW
        efficiency: list[float],  # % Fraction between 0 and 1
        fuel_rate: list[float],  # Sm3/day?
        load_unit: Unit,
        exceeds_maximum_load: list[bool],
        energy_usage: list[float],
        energy_usage_unit: Unit,
    ):
        super().__init__(
            energy_usage=energy_usage,
            energy_usage_unit=energy_usage_unit,
            power=load,
            power_unit=load_unit,
        )
        self.load = load
        self.load_unit = load_unit
        self.efficiency = efficiency
        self.fuel_rate = fuel_rate
        self.exceeds_maximum_load = exceeds_maximum_load

    @property
    def is_valid(self) -> list[bool]:
        return np.invert(self.exceeds_maximum_load).tolist()
