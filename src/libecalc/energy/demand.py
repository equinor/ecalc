from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Self

from libecalc.common.units import Unit


@dataclass(frozen=True)
class Demand(abc.ABC):
    """Base for all energy demand types.

    Additional carriers (e.g. ThermalPower/Steam) can be added as subclasses
    when thermal energy modeling is needed.
    """

    value: float

    def __post_init__(self) -> None:
        if self.value < 0:
            from libecalc.energy.errors import NegativeDemandError

            raise NegativeDemandError(self.value, type(self).__name__)

    @property
    @abc.abstractmethod
    def unit(self) -> Unit: ...

    def __add__(self, other: Self) -> Self:
        if type(self) is not type(other):
            msg = f"Cannot add {type(self).__name__} and {type(other).__name__}"
            raise TypeError(msg)
        return type(self)(value=self.value + other.value)

    def __sub__(self, other: Self) -> Self:
        if type(self) is not type(other):
            msg = f"Cannot subtract {type(other).__name__} from {type(self).__name__}"
            raise TypeError(msg)
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
