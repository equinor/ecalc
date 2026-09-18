from __future__ import annotations

from dataclasses import dataclass

from libecalc.energy.dispatch import DispatchStrategy
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnit


@dataclass(kw_only=True)
class TimeSeriesJunction(TimeSeriesEnergyUnit):
    dispatch_strategy: DispatchStrategy | None = None


@dataclass(kw_only=True)
class TimeSeriesElectricalBus(TimeSeriesJunction): ...


@dataclass(kw_only=True)
class TimeSeriesFuelGasManifold(TimeSeriesJunction): ...
