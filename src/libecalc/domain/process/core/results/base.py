from __future__ import annotations

import numpy as np

from libecalc.common.units import Unit


class EnergyModelBaseResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class EnergyFunctionResult(EnergyModelBaseResult):
    """energy_usage: Energy usage values [MW] or [Sm3/day]
    power: Power in MW if applicable.
    """

    def __init__(
        self,
        energy_usage: list[float],
        energy_usage_unit: Unit,
        power: list[float] | None = None,
        power_unit: Unit | None = Unit.MEGA_WATT,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.energy_usage = energy_usage
        self.energy_usage_unit = energy_usage_unit
        self.power = power
        self.power_unit = power_unit

    @property
    def is_valid(self) -> list[bool]:
        """We assume that all non-NaN results are valid calculation points except for a few exceptions where we override
        this method.
        """
        return list(~np.isnan(self.energy_usage))

    def __len__(self):
        return len(self.energy_usage)
