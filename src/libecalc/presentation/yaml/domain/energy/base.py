from __future__ import annotations

import abc
from collections.abc import Sequence
from typing import Final, Protocol, Self

from libecalc.common.ddd.entity import Entity
from libecalc.common.time_utils import Period
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.energy.energy_network_simulation import EnergyUnitFactory
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TimeSeriesEnergyUnit(Entity[EnergyUnitId]):
    def __init__(self, *, name: str, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._id: Final[EnergyUnitId] = energy_unit_id or self._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    @classmethod
    def _create_id(cls: type[Self]) -> EnergyUnitId:
        return EnergyUnitId(ecalc_id_generator())


class CreateEnergyUnit(Protocol):
    def __call__(self, demand: Energy, incoming_connections: Sequence[EnergyConnection]) -> EnergyUnit: ...


class ResolvedEnergyUnitFactory(EnergyUnitFactory):
    """A factory whose configuration is already resolved for a single period."""

    def __init__(
        self,
        *,
        energy_unit_id: EnergyUnitId,
        name: str,
        create: CreateEnergyUnit,
    ) -> None:
        self._id = energy_unit_id
        self._name = name
        self._create = create

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection]) -> EnergyUnit:
        return self._create(demand, incoming_connections)


class TimeSeriesEnergyUnitFactory(TimeSeriesEnergyUnit, abc.ABC):
    """Holds time series configuration and resolves it into a period-agnostic factory."""

    def __init__(
        self,
        *,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.capacity = capacity

    @abc.abstractmethod
    def resolve(self, period: Period) -> EnergyUnitFactory: ...
