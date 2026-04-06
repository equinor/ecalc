from __future__ import annotations

import abc
import uuid
from typing import TYPE_CHECKING, NewType, Set
from uuid import UUID

from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.process_system.stream_propagator import StreamPropagator

if TYPE_CHECKING:
    from collections.abc import Sequence

    from libecalc.domain.process.process_system.process_unit import ProcessUnit

PORT_ID = str

ProcessSystemId = NewType("ProcessSystemId", UUID)


def create_process_system_id() -> ProcessSystemId:
    return ProcessSystemId(uuid.uuid4())


class ProcessSystem(StreamPropagator, abc.ABC):
    @abc.abstractmethod
    def get_process_units(self) -> Sequence[ProcessUnit | ProcessSystem]: ...

    @abc.abstractmethod
    def get_id(self) -> ProcessSystemId: ...

    @abc.abstractmethod
    def get_process_systems(self) -> set[ProcessSystem]:
        ...

    @abc.abstractmethod
    def get_process_system_unit_pairs(self) -> dict[ProcessUnitId | ProcessSystemId, ProcessSystemId]:
        """
        Temporary, for every process unit (recursively), get the associated Process system id (if any)
        Currently a process unit can only belong directly to one process system "parent"
        """
        ...