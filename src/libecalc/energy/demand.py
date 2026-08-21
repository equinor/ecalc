from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Self

from libecalc.common.units import Unit


@dataclass(frozen=True)
class Demand(abc.ABC):
    """Base for all energy demand types."""

    value: float

    @property
    @abc.abstractmethod
    def unit(self) -> Unit: ...

    def __add__(self, other: Self) -> Self:
        return type(self)(value=self.value + other.value)

    def __sub__(self, other: Self) -> Self:
        return type(self)(value=self.value - other.value)


@dataclass(frozen=True)
class MechanicalPower(Demand):
    @property
    def unit(self) -> Unit:
        return Unit.MEGA_WATT


@dataclass(frozen=True)
class ElectricalPower(Demand):
    @property
    def unit(self) -> Unit:
        return Unit.MEGA_WATT


@dataclass(frozen=True)
class FuelGasRate(Demand):
    @property
    def unit(self) -> Unit:
        return Unit.STANDARD_CUBIC_METER_PER_DAY


@dataclass(frozen=True)
class DieselRate(Demand):
    @property
    def unit(self) -> Unit:
        return Unit.LITRES_PER_DAY
