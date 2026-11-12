from typing import Final, Self

from libecalc.common.ddd import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.ecalc_model.equipment.equipment_id import EquipmentId


class CompressorEquipment(Entity[EquipmentId]):
    """
    A physical compressor. Process and energy units reference it by its equipment id, but have their own ids.

    Identity is the id. The name and alias are display data and may change, e.g. from a temporary name to the
    equipment tag once the equipment is registered.
    """

    def __init__(self, name: str, alias: str | None = None, compressor_equipment_id: EquipmentId | None = None):
        self._id: Final[EquipmentId] = compressor_equipment_id or CompressorEquipment._create_id()
        self._name = name
        self._alias = alias

    def get_id(self) -> EquipmentId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> EquipmentId:
        return EquipmentId(ecalc_id_generator())

    @property
    def name(self) -> str:
        return self._name

    @property
    def alias(self) -> str | None:
        return self._alias
