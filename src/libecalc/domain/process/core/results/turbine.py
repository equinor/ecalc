from __future__ import annotations

import numpy as np

from libecalc.common.units import Unit
from libecalc.domain.process.core.results import EnergyFunctionResult
from libecalc.domain.process.core.results.base import EnergyResult, Quantity


class TurbineResult(EnergyFunctionResult):
    def __init__(
        self,
        load: list[float],  # MW
        efficiency: list[float],  # % Fraction between 0 and 1
        load_unit: Unit,
        exceeds_maximum_load: list[bool],
        energy_usage: list[float],
        energy_usage_unit: Unit,
    ):
        self._energy_usage = energy_usage
        self._energy_usage_unit = energy_usage_unit
        self._power = load
        self._power_unit: Unit = load_unit if load_unit is not None else Unit.MEGA_WATT
        self.efficiency = efficiency
        self.exceeds_maximum_load = exceeds_maximum_load

    def get_energy_result(self) -> EnergyResult:
        return EnergyResult(
            energy_usage=Quantity(
                values=self._energy_usage,
                unit=self._energy_usage_unit,
            ),
            power=Quantity(
                values=self._power,
                unit=self._power_unit,
            )
            if self._power is not None
            else None,
            is_valid=self._is_valid,
        )

    @property
    def _is_valid(self) -> list[bool]:
        return np.invert(self.exceeds_maximum_load).tolist()
