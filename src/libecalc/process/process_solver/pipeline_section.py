from typing import Final, Self

from libecalc.common.ddd import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId, ProcessPipelineSectionId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import ConfigurationHandlerId
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import RootFindingStrategy


class PipelineSection(Entity[ProcessPipelineSectionId]):
    """A self-contained, solvable single-shaft process pipeline section"""

    def __init__(
        self,
        shaft_id: ConfigurationHandlerId,
        runner: ProcessRunner,
        anti_surge_strategy: AntiSurgeStrategy,
        pressure_control_strategy: PressureControlStrategy,
        speed_boundary: Boundary,
        root_finding_strategy: RootFindingStrategy,
        process_pipeline_id: ProcessPipelineId,
        process_pipeline_section_id: ProcessPipelineSectionId | None = None,
    ):
        self._id: Final[ProcessPipelineSectionId] = process_pipeline_section_id or PipelineSection._create_id()
        self._process_pipeline_id: Final[ProcessPipelineId] = process_pipeline_id
        self._shaft_id: Final[ConfigurationHandlerId] = shaft_id
        self._runner: Final[ProcessRunner] = runner
        self._anti_surge_strategy: AntiSurgeStrategy = anti_surge_strategy
        self._pressure_control_strategy: PressureControlStrategy = pressure_control_strategy
        self._speed_boundary: Boundary = speed_boundary
        self._root_finding_strategy: RootFindingStrategy = root_finding_strategy

    def get_id(self) -> ProcessPipelineSectionId:
        return self._id

    def get_process_pipeline_id(self) -> ProcessPipelineId:
        return self._process_pipeline_id

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessPipelineSectionId:
        return ProcessPipelineSectionId(ecalc_id_generator())

    def get_shaft_id(self) -> ConfigurationHandlerId:
        return self._shaft_id

    def get_runner(self) -> ProcessRunner:
        return self._runner

    def get_anti_surge_strategy(self) -> AntiSurgeStrategy:
        return self._anti_surge_strategy

    def get_pressure_control_strategy(self) -> PressureControlStrategy:
        return self._pressure_control_strategy

    def get_speed_boundary(self) -> Boundary:
        return self._speed_boundary

    def get_root_finding_strategy(self) -> RootFindingStrategy:
        return self._root_finding_strategy


# This is currently the aggregate as this is the interface to solve, and it delegates further to sections etc
class Pipeline(Entity[ProcessPipelineId]):
    def __init__(
        self,
        process_pipeline_sections: list[PipelineSection],
        process_pipeline_id: ProcessPipelineId | None = None,
    ):
        self._id: Final[ProcessPipelineId] = process_pipeline_id or Pipeline._create_id()
        self._process_pipeline_sections: Final[list[PipelineSection]] = process_pipeline_sections

    def get_id(self) -> ProcessPipelineId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessPipelineId:
        return ProcessPipelineId(ecalc_id_generator())

    def get_process_pipeline_sections(self) -> list[PipelineSection]:
        return self._process_pipeline_sections
