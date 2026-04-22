import abc
import uuid
from typing import NewType
from uuid import UUID

from libecalc.domain.process.process_pipeline.stream_propagator import StreamPropagator

ProcessUnitId = NewType("ProcessUnitId", UUID)


def create_process_unit_id() -> ProcessUnitId:
    return ProcessUnitId(uuid.uuid4())


class ProcessUnit(StreamPropagator, abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> ProcessUnitId: ...
