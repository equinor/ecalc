import abc
from typing import Any, NewType, Protocol, Self
from uuid import UUID

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

ProcessUnitId = NewType("ProcessUnitId", UUID)


def create_process_unit_id() -> ProcessUnitId:
    """Standalone id factory for units not extending GasProcessUnit (e.g. Pump, DirectMixer)."""
    return ProcessUnitId(ecalc_id_generator())


class ProcessUnit(Protocol):
    """Any unit that can participate in a process pipeline.

    Satisfied structurally by Compressor, Pump, DirectMixer, DirectSplitter,
    and any other unit with get_id() and propagate_stream().
    """

    def get_id(self) -> ProcessUnitId: ...

    def propagate_stream(self, inlet_stream: Any) -> Any: ...


class GasProcessUnit(Entity[ProcessUnitId], abc.ABC):
    """Process unit operating on gas streams (FluidStream)."""

    @abc.abstractmethod
    def get_id(self) -> ProcessUnitId: ...

    @abc.abstractmethod
    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream: ...

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessUnitId:
        return ProcessUnitId(ecalc_id_generator())
