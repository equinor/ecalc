from collections.abc import Sequence
from typing import Final, NewType, Self
from uuid import UUID

from libecalc.common.ddd import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.ecalc_model.compressor_equipment import CompressorId

ShaftId = NewType("ShaftId", UUID)


class ShaftEquipment(Entity[ShaftId]):
    """
    A physical shaft and the compressors on it, as declared in the model.

    Not the process solver's shaft: the solver creates its own shafts from this membership.
    """

    def __init__(self, name: str, compressor_ids: Sequence[CompressorId], shaft_id: ShaftId | None = None):
        self._id: Final[ShaftId] = shaft_id or ShaftEquipment._create_id()
        self._name = name
        self._compressor_ids = tuple(compressor_ids)

    def get_id(self) -> ShaftId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> ShaftId:
        return ShaftId(ecalc_id_generator())

    @property
    def name(self) -> str:
        return self._name

    @property
    def compressor_ids(self) -> tuple[CompressorId, ...]:
        """The compressors on the shaft, in the order SHAFTS lists them."""
        return self._compressor_ids
