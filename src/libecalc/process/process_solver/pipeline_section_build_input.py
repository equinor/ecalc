"""
Process-side input objects for pipeline section preparation.

These objects define the explicit process-owned input shape used to prepare
runtime PipelineSection objects without depending on ecalc_model.
"""

from collections.abc import Sequence

from libecalc.common.ddd import value_object
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType


@value_object
class PressureControlInput:
    type: PressureControlType


@value_object
class AntiSurgeInput:
    type: AntiSurgeType


@value_object
class PipelineSectionBuildConstraint:
    pressure_control: PressureControlInput
    anti_surge: AntiSurgeInput


@value_object
class PipelineSectionBuildProblemSection:
    process_unit_ids: Sequence[ProcessUnitId]
    configuration_handlers: Sequence[ConfigurationHandler]
    constraint: PipelineSectionBuildConstraint


@value_object
class PipelineSectionBuildProblem:
    process_pipeline_id: ProcessPipelineId
    configuration_handlers: Sequence[ConfigurationHandler]
    process_problem_sections: Sequence[PipelineSectionBuildProblemSection]
