from __future__ import annotations

import abc
import uuid
from typing import TYPE_CHECKING, NewType
from uuid import UUID

from libecalc.domain.process.entities.shaft.shaft import MechanicalComponent
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
    def get_mechanical_components(self) -> list[MechanicalComponent]: ...
    """
    Temp for mechanical components, but they may eventually be moved to a separate system, e.g. MechanicalSystem, that can be linked to the ProcessSystem?
    """
