from __future__ import annotations

import abc
import uuid
from typing import TYPE_CHECKING, NewType
from uuid import UUID

from libecalc.domain.process.process_system.process_unit import ProcessUnit
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
