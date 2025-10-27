from __future__ import annotations

import numpy as np

from libecalc.common.units import Unit
from libecalc.domain.process.core.results.base import EnergyFunctionResult, EnergyResult, Quantity


class EnergyFunctionGenericResult(EnergyFunctionResult):
    def __init__(
        self,
        energy_usage: list[float],
        energy_usage_unit: Unit,
        power: list[float] | None,
        power_unit: Unit | None,
        allow_negative_energy_usage: bool = False,
    ):
        self._energy_usage = energy_usage
        self._energy_usage_unit = energy_usage_unit
        self._power = power
        self._power_unit: Unit = power_unit if power_unit is not None else Unit.MEGA_WATT
        self._allow_negative_energy_usage = allow_negative_energy_usage

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
        """We assume that all non-NaN results are valid calculation points except for a few exceptions where we override
        this method.
        """
        is_valid = ~np.isnan(self._energy_usage)
        if not self._allow_negative_energy_usage:
            is_valid[np.asarray(self._energy_usage) < 0] = False
        return is_valid.tolist()
