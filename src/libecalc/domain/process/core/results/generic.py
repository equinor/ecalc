from __future__ import annotations

import numpy as np

from libecalc.common.units import Unit
from libecalc.domain.process.core.results.base import EnergyFunctionResult


class EnergyFunctionGenericResult(EnergyFunctionResult):
    def __init__(
        self,
        energy_usage: list[float],
        energy_usage_unit: Unit,
        power: list[float] | None,
        power_unit: Unit | None,
        allow_negative_energy_usage: bool = False,
    ):
        super().__init__(
            energy_usage=energy_usage,
            energy_usage_unit=energy_usage_unit,
            power=power,
            power_unit=power_unit,
        )
        self._allow_negative_energy_usage = allow_negative_energy_usage

    @property
    def is_valid(self) -> list[bool]:
        """We assume that all non-NaN results are valid calculation points except for a few exceptions where we override
        this method.
        """
        is_valid = ~np.isnan(self.energy_usage)
        if not self._allow_negative_energy_usage:
            is_valid[np.asarray(self.energy_usage) < 0] = False
        return is_valid.tolist()
