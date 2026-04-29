import abc
from typing import NewType, Protocol, Self, runtime_checkable
from uuid import UUID

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.process_pipeline.stream_propagator import StreamPropagator
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

ProcessUnitId = NewType("ProcessUnitId", UUID)


class ProcessUnit(Entity[ProcessUnitId], StreamPropagator, abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> ProcessUnitId: ...

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessUnitId:
        return ProcessUnitId(ecalc_id_generator())


@runtime_checkable
class RateConstrainedUnit(Protocol):
    """Process units with a maximum inlet standard rate."""

    def get_id(self) -> ProcessUnitId: ...

    def get_maximum_standard_rate(self, inlet_stream: FluidStream) -> float: ...
