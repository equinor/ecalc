from libecalc.common.ddd import value_object
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId, ProcessPipelineSectionId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import ConfigurationHandlerId
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import RootFindingStrategy

# TODO: Change to entities


@value_object
class PipelineSection:
    """A self-contained, solvable single-shaft process pipeline section"""

    shaft_id: ConfigurationHandlerId
    # We currently set this to have a reference to the pipeline when needed, since that is e.g. what we expose to users
    process_pipeline_id: ProcessPipelineId
    process_pipeline_section_id: ProcessPipelineSectionId
    runner: ProcessRunner
    anti_surge_strategy: AntiSurgeStrategy
    pressure_control_strategy: PressureControlStrategy
    speed_boundary: Boundary
    root_finding_strategy: RootFindingStrategy


# This is currently the aggregate as this is the interface to solve, and it delegates further to sections etc
@value_object
class Pipeline:
    process_pipeline_id: ProcessPipelineId
    pipeline_sections: list[PipelineSection]
