from __future__ import annotations

import abc

from libecalc.common.units import Unit


class EnergyModelBaseResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class EnergyFunctionResult(abc.ABC):
    """energy_usage: Energy usage values [MW] or [Sm3/day]
    power: Power in MW if applicable.
    """

    def __init__(
        self,
        energy_usage: list[float],
        energy_usage_unit: Unit,
        power: list[float] | None,
        power_unit: Unit | None,
    ):
        self.energy_usage = energy_usage
        self.energy_usage_unit = energy_usage_unit
        self.power = power
        self.power_unit: Unit = power_unit if power_unit is not None else Unit.MEGA_WATT

    @property
    @abc.abstractmethod
    def is_valid(self) -> list[bool]: ...

    def __len__(self):
        return len(self.energy_usage)
