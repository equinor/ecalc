from typing import Final, NewType, Self
from uuid import UUID

from libecalc.common.ddd import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator

CompressorId = NewType("CompressorId", UUID)


class CompressorEquipment(Entity[CompressorId]):
    """
    A physical compressor, shared by the process and energy domains through its id.

    Identity is the id. The name and alias are display data and may change, e.g. from a temporary name to the
    equipment tag once the equipment is registered.
    """

    def __init__(self, name: str, alias: str | None = None, compressor_id: CompressorId | None = None):
        self._id: Final[CompressorId] = compressor_id or CompressorEquipment._create_id()
        self._name = name
        self._alias = alias

    def get_id(self) -> CompressorId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> CompressorId:
        return CompressorId(ecalc_id_generator())

    @property
    def name(self) -> str:
        return self._name

    @property
    def alias(self) -> str | None:
        return self._alias
