from __future__ import annotations

import abc
from abc import abstractmethod
from typing import Final, Self

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.energy.energy_failure import EnergyFailure
from libecalc.energy.energy_types import Energy
from libecalc.energy.ids import EnergyConnectionId, EnergyUnitId


class EnergyUnit(Entity[EnergyUnitId], abc.ABC):
    """Base for all energy domain components with identity."""

    def __init__(
        self,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        self._name = name
        self._id: Final[EnergyUnitId] = energy_unit_id or self._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    @abstractmethod
    def get_input_energy_type(self) -> type[Energy] | None: ...

    @abstractmethod
    def get_output_energy_type(self) -> type[Energy] | None: ...

    @abstractmethod
    def get_input_energies(self) -> dict[EnergyConnectionId, Energy]:
        """Return energy for every incoming connection, including zero flows; sources return an empty mapping."""
        ...

    @abstractmethod
    def get_failures(self) -> list[EnergyFailure]:
        """Report how this unit fails to meet what the network asks of it, if at all."""
        ...

    @classmethod
    def _create_id(cls: type[Self]) -> EnergyUnitId:
        return EnergyUnitId(ecalc_id_generator())
