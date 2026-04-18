"""Thin protocols that infrastructure models satisfy."""

from typing import Protocol


class TurbineEnergyUsage(Protocol):
    values: list[float]


class TurbineEnergyResult(Protocol):
    energy_usage: TurbineEnergyUsage


class TurbineResult(Protocol):
    exceeds_maximum_load: list[bool]

    def get_energy_result(self) -> TurbineEnergyResult: ...


class TurbineDriver(Protocol):
    """Anything that converts mechanical load [MW] to fuel, with load limits."""

    def evaluate(self, load) -> TurbineResult: ...

    @property
    def max_power(self) -> float: ...


class FuelConverter(Protocol):
    """Anything that converts electrical power [MW] to fuel [Sm³/day]."""

    def evaluate_fuel_usage(self, power_mw: float) -> float: ...

    def evaluate_power_capacity_margin(self, power_mw: float) -> float: ...
