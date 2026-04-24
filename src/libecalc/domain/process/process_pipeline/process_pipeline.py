import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import NewType
from uuid import UUID

from libecalc.domain.process.process_pipeline.process_unit import ProcessUnit

ProcessPipelineId = NewType("ProcessPipelineId", UUID)


def create_process_pipeline_id() -> ProcessPipelineId:
    return ProcessPipelineId(uuid.uuid4())


@dataclass
class ProcessPipeline:  # or simulator?
    id: ProcessPipelineId
    stream_propagators: Sequence[ProcessUnit]

    def get_process_units(self) -> list[ProcessUnit]:
        return list(self.stream_propagators)
