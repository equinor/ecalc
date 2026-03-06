import abc
import uuid
from typing import NewType
from uuid import UUID

from libecalc.domain.process.value_objects.fluid_stream import FluidStream

ProcessUnitId = NewType("ProcessUnitId", UUID)


def create_process_unit_id() -> ProcessUnitId:
    return ProcessUnitId(uuid.uuid4())


class ProcessUnit(abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> ProcessUnitId: ...

    @abc.abstractmethod
    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream: ...
