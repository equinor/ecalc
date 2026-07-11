import abc
from abc import abstractmethod
from typing import NewType, Self
from uuid import UUID

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.process_pipeline.stream_propagator import StreamPropagator

ProcessUnitId = NewType("ProcessUnitId", UUID)


class ProcessUnit[TSnapshot](Entity[ProcessUnitId], StreamPropagator, abc.ABC):
    @abstractmethod
    def get_id(self) -> ProcessUnitId: ...

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessUnitId:
        return ProcessUnitId(ecalc_id_generator())

    @abstractmethod
    def _record_snapshot(self, key: object, snapshot: TSnapshot) -> None: ...

    @abstractmethod
    def snapshot_for(self, key: object) -> TSnapshot | None: ...

    @abstractmethod
    @property
    def history(self) -> list[TSnapshot]: ...
