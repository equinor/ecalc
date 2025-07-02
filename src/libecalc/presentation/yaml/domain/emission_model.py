import abc

from libecalc.domain.common.entity import Entity
from libecalc.domain.energy import Emitter
from libecalc.domain.infrastructure.path_id import PathID


class EmissionContainer(Entity[PathID]):
    def __init__(self, entity_id: PathID, parent_container: PathID = None) -> None:
        super().__init__(entity_id=entity_id)
        self._parent_container = parent_container


class EmissionRegistry(abc.ABC):
    @abc.abstractmethod
    def add_container(self, container: EmissionContainer): ...

    @abc.abstractmethod
    def add_emitter(self, emitter: Emitter, parent_container_id: PathID): ...
