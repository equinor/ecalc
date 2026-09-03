from __future__ import annotations

import abc
from typing import Final, NewType, Self
from uuid import UUID

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator

EnergyUnitId = NewType("EnergyUnitId", UUID)


class EnergyUnit(Entity[EnergyUnitId], abc.ABC):
    """Base for all energy domain components with identity."""

    def __init__(self, name: str, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._id: Final[EnergyUnitId] = energy_unit_id or self._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    @classmethod
    def _create_id(cls: type[Self]) -> EnergyUnitId:
        return EnergyUnitId(ecalc_id_generator())
