import abc
import uuid
from typing import NewType
from uuid import UUID

from libecalc.domain.process.process_system.stream_propagator import StreamPropagator

PORT_ID = str

ProcessSystemId = NewType("ProcessSystemId", UUID)


def create_process_system_id() -> ProcessSystemId:
    return ProcessSystemId(uuid.uuid4())


class ProcessSystem(StreamPropagator, abc.ABC):
    @abc.abstractmethod
    def get_process_units(self): ...

    @abc.abstractmethod
    def get_id(self) -> ProcessSystemId: ...
