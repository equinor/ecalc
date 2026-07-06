from collections.abc import Sequence
from typing import Final, NewType, Self
from uuid import UUID

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.process_pipeline.process_unit import ProcessUnit

ProcessPipelineId = NewType("ProcessPipelineId", UUID)
ProcessPipelineSectionId = NewType("ProcessPipelineSectionId", UUID)


class ProcessPipelineSection(Entity[ProcessPipelineSectionId]):
    def __init__(
        self,
        process_units: Sequence[ProcessUnit],  # TODO: Reassure they are in order
        process_pipeline_section_id: ProcessPipelineSectionId | None = None,
    ):
        self._process_units = process_units
        self._id: Final[ProcessPipelineSectionId] = process_pipeline_section_id or ProcessPipelineSection._create_id()

    def get_id(self) -> ProcessPipelineSectionId:
        return self._id

    def get_process_units(self) -> list[ProcessUnit]:
        return list(self._process_units)

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessPipelineSectionId:
        return ProcessPipelineSectionId(ecalc_id_generator())

    def __str__(self):
        return f"ProcessPipelineSection(process_pipeline_section_id={self._id}, process_units={self._process_units})"


class ProcessPipeline(Entity[ProcessPipelineId]):
    def __init__(
        self,
        name: str,
        process_pipeline_sections: Sequence[ProcessPipelineSection],  # TODO: Reassure that they are in order
        process_pipeline_id: ProcessPipelineId | None = None,
        # TODO: Start and end process units to not belong to a section but to a pipeline?
    ):
        self._name = name
        self._process_pipeline_sections = process_pipeline_sections
        self._id: Final[ProcessPipelineId] = process_pipeline_id or ProcessPipeline._create_id()

    def get_id(self) -> ProcessPipelineId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_process_pipeline_sections(self) -> Sequence[ProcessPipelineSection]:
        return self._process_pipeline_sections

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessPipelineId:
        return ProcessPipelineId(ecalc_id_generator())

    def __str__(self):
        return f"ProcessPipeline(process_pipeline_id={self._id}, name={self._name}, process_pipeline_sections={self._process_pipeline_sections})"
