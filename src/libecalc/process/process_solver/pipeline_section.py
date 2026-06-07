from libecalc.common.ddd import value_object
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import ConfigurationHandlerId
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import RootFindingStrategy


@value_object
class PipelineSection:
    """A self-contained, solvable single-shaft process pipeline section"""

    shaft_id: ConfigurationHandlerId
    process_pipeline_id: ProcessPipelineId
    runner: ProcessRunner
    anti_surge_strategy: AntiSurgeStrategy
    pressure_control_strategy: PressureControlStrategy
    speed_boundary: Boundary
    root_finding_strategy: RootFindingStrategy
