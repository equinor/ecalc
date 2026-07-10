"""
Process-side input objects for building pipeline sections.

These objects define the explicit process-owned input shape used to build
runtime PipelineSection objects without depending on ecalc_model.
"""

from collections.abc import Sequence

from libecalc.common.ddd import value_object
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId, ProcessPipelineSectionId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType


@value_object
class BuildPipelineSectionInput:
    process_pipeline_section_id: ProcessPipelineSectionId
    pressure_control: PressureControlType
    anti_surge: AntiSurgeType


@value_object
class BuildPipelineSectionsInput:
    process_pipeline_id: ProcessPipelineId
    configuration_handlers: Sequence[ConfigurationHandler]
    sections: Sequence[BuildPipelineSectionInput]
