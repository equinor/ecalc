from __future__ import annotations

import abc
from typing import NewType, Self
from uuid import UUID

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator

EnergyUnitId = NewType("EnergyUnitId", UUID)


class EnergyUnit(Entity[EnergyUnitId], abc.ABC):
    """Base for all energy domain components with identity."""

    @abc.abstractmethod
    def get_id(self) -> EnergyUnitId: ...

    @classmethod
    def _create_id(cls: type[Self]) -> EnergyUnitId:
        return EnergyUnitId(ecalc_id_generator())
