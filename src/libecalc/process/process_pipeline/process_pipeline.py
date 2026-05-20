from collections.abc import Sequence
from typing import Final, NewType, Self
from uuid import UUID

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.process_pipeline.process_unit import ProcessUnit

ProcessPipelineId = NewType("ProcessPipelineId", UUID)


class ProcessPipeline(Entity[ProcessPipelineId]):
    def __init__(
        self, name: str, stream_propagators: Sequence[ProcessUnit], process_pipeline_id: ProcessPipelineId | None = None
    ):
        self._name = name
        self._stream_propagators = stream_propagators
        self._id: Final[ProcessPipelineId] = process_pipeline_id or ProcessPipeline._create_id()

    def get_id(self) -> ProcessPipelineId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_process_units(self) -> list[ProcessUnit]:
        return list(self._stream_propagators)

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessPipelineId:
        return ProcessPipelineId(ecalc_id_generator())

    def __str__(self):
        return f"ProcessPipeline(process_pipeline_id={self._id}, name={self._name}, stream_propagators={self._stream_propagators})"
