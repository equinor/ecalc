from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.energy.energy_network_simulation import EnergyUnitFactory
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


def _generate_id() -> EnergyUnitId:
    return EnergyUnitId(ecalc_id_generator())


@dataclass(kw_only=True)
class TimeSeriesEnergyUnit:
    name: str
    energy_unit_id: EnergyUnitId = field(default_factory=_generate_id)

    def get_id(self) -> EnergyUnitId:
        return self.energy_unit_id

    def get_name(self) -> str:
        return self.name


@dataclass(kw_only=True)
class TimeSeriesEnergyUnitFactory(TimeSeriesEnergyUnit, EnergyUnitFactory, abc.ABC):
    capacity: TimeSeriesExpression | None = None

    @abc.abstractmethod
    def create(self, demand: Energy, capacity: Energy | None, **extra: Any) -> EnergyUnit: ...
