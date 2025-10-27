from __future__ import annotations

import abc
from dataclasses import dataclass

from libecalc.common.units import Unit


@dataclass
class Quantity:
    values: list[float]
    unit: Unit

    def __len__(self):
        return len(self.values)


@dataclass
class EnergyResult:
    energy_usage: Quantity
    power: Quantity | None
    is_valid: list[bool]


class EnergyFunctionResult(abc.ABC):
    """energy_usage: Energy usage values [MW] or [Sm3/day]
    power: Power in MW if applicable.
    """

    @abc.abstractmethod
    def get_energy_result(self) -> EnergyResult: ...
