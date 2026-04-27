from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import NewType, Self
from uuid import UUID

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.process_pipeline.process_unit import ProcessUnit

ProcessPipelineId = NewType("ProcessPipelineId", UUID)


@dataclass
class ProcessPipeline(Entity[ProcessPipelineId]):
    stream_propagators: Sequence[ProcessUnit]
    _id: ProcessPipelineId = field(default_factory=lambda: ProcessPipeline._create_id())

    def get_process_units(self) -> list[ProcessUnit]:
        return list(self.stream_propagators)

    def get_id(self) -> ProcessPipelineId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessPipelineId:
        return ProcessPipelineId(ecalc_id_generator())
