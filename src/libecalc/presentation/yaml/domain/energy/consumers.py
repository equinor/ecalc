from __future__ import annotations

from dataclasses import dataclass

from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnit
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(kw_only=True)
class TimeSeriesConsumer(TimeSeriesEnergyUnit):
    demand: TimeSeriesExpression | None = None


@dataclass(kw_only=True)
class TimeSeriesElectricalConsumer(TimeSeriesConsumer): ...


@dataclass(kw_only=True)
class TimeSeriesMechanicalConsumer(TimeSeriesConsumer): ...


@dataclass(kw_only=True)
class TimeSeriesFuelGasConsumer(TimeSeriesConsumer): ...


@dataclass(kw_only=True)
class TimeSeriesDieselConsumer(TimeSeriesConsumer): ...
