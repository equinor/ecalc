import abc
from typing import Self

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.process_pipeline.ids import ProcessUnitId
from libecalc.process.process_pipeline.stream_propagator import StreamPropagator


class ProcessUnit(Entity[ProcessUnitId], StreamPropagator, abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> ProcessUnitId: ...

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessUnitId:
        return ProcessUnitId(ecalc_id_generator())
