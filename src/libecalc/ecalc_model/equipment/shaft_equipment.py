from collections.abc import Sequence
from typing import Final, Self

from libecalc.common.ddd import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.ecalc_model.equipment.equipment_id import EquipmentId


class ShaftEquipment(Entity[EquipmentId]):
    """
    A physical shaft and the compressors on it, as declared in the model.

    Not the process solver's shaft: the solver creates its own shafts from this membership.
    """

    def __init__(self, name: str, compressor_equipment_ids: Sequence[EquipmentId], shaft_id: EquipmentId | None = None):
        self._id: Final[EquipmentId] = shaft_id or ShaftEquipment._create_id()
        self._name = name
        self._compressor_equipment_ids = tuple(compressor_equipment_ids)

    def get_id(self) -> EquipmentId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> EquipmentId:
        return EquipmentId(ecalc_id_generator())

    @property
    def name(self) -> str:
        return self._name

    @property
    def compressor_equipment_ids(self) -> tuple[EquipmentId, ...]:
        """The compressors on the shaft, in the order SHAFTS lists them."""
        return self._compressor_equipment_ids
