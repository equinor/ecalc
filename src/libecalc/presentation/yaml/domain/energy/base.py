from __future__ import annotations

from typing import Final, Self

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.energy.energy_unit import EnergyUnitId
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


class TimeSeriesEnergyUnitFactory(TimeSeriesEnergyUnit):
    """Holds time series configuration for an energy unit."""

    def __init__(
        self,
        *,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.capacity = capacity
