import uuid

from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.node import PhysicalUnit


class GeneratorPhysicalUnit(PhysicalUnit):
    def __init__(self, path_id: PathID):
        self._path_id = path_id

    def get_unit_id(self) -> uuid.UUID:
        return self._path_id.get_model_unique_id()

    def get_name(self) -> str:
        return self._path_id.get_name()
