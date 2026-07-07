"""
Process-side contracts for pipeline section preparation.

The concrete process problem model lives in ecalc_model, which process should
not import. These protocols keep the solver typed while avoiding dependency to
ecalc_model.
"""

from collections.abc import Sequence
from typing import Protocol

from libecalc.common.time_utils import Period
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType


class PressureTargetInput(Protocol):
    def get_periods(self) -> Sequence[Period]: ...

    def get_masked_values(self) -> Sequence[float]: ...


class PressureControlInput(Protocol):
    type: PressureControlType


class AntiSurgeInput(Protocol):
    type: AntiSurgeType


class ProcessSectionConstraintInput(Protocol):
    outlet_pressure: PressureTargetInput
    pressure_control: PressureControlInput
    anti_surge: AntiSurgeInput
    target_process_unit_id: ProcessUnitId


class ProcessProblemSectionInput(Protocol):
    process_unit_ids: Sequence[ProcessUnitId]
    configuration_handlers: Sequence[ConfigurationHandler]
    constraint: ProcessSectionConstraintInput


class ProcessProblemInput(Protocol):
    process_pipeline_id: ProcessPipelineId
    configuration_handlers: Sequence[ConfigurationHandler]
    process_problem_sections: Sequence[ProcessProblemSectionInput]
