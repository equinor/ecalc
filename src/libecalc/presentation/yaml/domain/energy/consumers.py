from __future__ import annotations

import abc
from collections.abc import Callable
from dataclasses import dataclass

from libecalc.common.time_utils import Period
from libecalc.energy import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnit
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


def expression_demand(
    expression: TimeSeriesExpression | None, energy_type: type[Energy]
) -> Callable[[Period], Energy | None]:
    def demand(period: Period) -> Energy | None:
        if expression is None:
            return None
        return energy_type(value=expression.get_value(period))

    return demand


@dataclass(kw_only=True)
class TimeSeriesConsumer(TimeSeriesEnergyUnit, abc.ABC):
    demand: Callable[[Period], Energy | None]

    def get_demand(self, period: Period) -> Energy | None:
        return self.demand(period)

    @classmethod
    @abc.abstractmethod
    def get_input_energy_type(cls) -> type[Energy]: ...


@dataclass(kw_only=True)
class TimeSeriesElectricalConsumer(TimeSeriesConsumer):
    @classmethod
    def get_input_energy_type(cls) -> type[Energy]:
        return ElectricalPower


@dataclass(kw_only=True)
class TimeSeriesMechanicalConsumer(TimeSeriesConsumer):
    @classmethod
    def get_input_energy_type(cls) -> type[Energy]:
        return MechanicalPower


@dataclass(kw_only=True)
class TimeSeriesFuelGasConsumer(TimeSeriesConsumer):
    @classmethod
    def get_input_energy_type(cls) -> type[Energy]:
        return FuelGasRate


@dataclass(kw_only=True)
class TimeSeriesDieselConsumer(TimeSeriesConsumer):
    @classmethod
    def get_input_energy_type(cls) -> type[Energy]:
        return DieselRate
