from __future__ import annotations

import abc
from dataclasses import dataclass

from libecalc.energy import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnit
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(kw_only=True)
class TimeSeriesConsumer(TimeSeriesEnergyUnit, abc.ABC):
    demand: TimeSeriesExpression | None = None

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
