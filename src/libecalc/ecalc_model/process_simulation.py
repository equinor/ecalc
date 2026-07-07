from collections.abc import Sequence
from typing import Final, NewType, Self, assert_never
from uuid import UUID

from libecalc.common.ddd import value_object
from libecalc.common.ddd.entity import Entity
from libecalc.common.time_utils import Period
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.ecalc_model.time_series_configuration import (
    TimeSeriesMixerConfiguration,
    TimeSeriesPressureDropperConfiguration,
    TimeSeriesSplitterConfiguration,
    TimeSeriesTemperatureSetterConfiguration,
)
from libecalc.ecalc_model.time_series_stream import TimeSeriesStream
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.process.process_pipeline.process_pipeline import (
    ProcessPipelineId,
    ProcessPipelineSectionId,
    ProcessUnitConnectionId,
)
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import (
    PressureControlType,
)
from libecalc.process.stream_distribution.common_stream_distribution import Overflow


@value_object
class CommonStreamSettings:
    rate_fractions: list[TimeSeriesExpression]
    overflow: list[Overflow]


@value_object
class CommonStreamDistributionConfig:  # TODO: Rather a strategy that splits a stream in a method according to a policy?
    inlet_stream: TimeSeriesStream
    settings: list[CommonStreamSettings]


@value_object
class IndividualStreamDistributionConfig:
    inlet_streams: list[TimeSeriesStream]


@value_object
class PressureControlConfig:  # Spec
    type: PressureControlType


@value_object
class AntiSurgeConfig:
    type: AntiSurgeType


@value_object
class Constraint:
    outlet_pressure: TimeSeriesExpression
    target_process_unit_id: ProcessUnitId
    target_process_connection_id: ProcessUnitConnectionId  # Currently the outlet of the process_unit above


ProcessProblemId = NewType("ProcessProblemId", UUID)
ProcessProblemSectionId = NewType("ProcessProblemSectionId", UUID)


class ProcessProblemSection(Entity[ProcessProblemSectionId]):
    def __init__(
        self,
        process_pipeline_section_id: ProcessPipelineSectionId,
        constraint: Constraint,
        pressure_control: PressureControlConfig,
        anti_surge: AntiSurgeConfig,
        process_problem_section_id: ProcessProblemSectionId | None = None,
    ):
        self._process_pipeline_section_id = process_pipeline_section_id
        self._constraint = constraint
        self._pressure_control = pressure_control
        self._anti_surge = anti_surge
        self._id: Final[ProcessProblemSectionId] = process_problem_section_id or ProcessProblemSection._create_id()

    def get_id(self) -> ProcessProblemSectionId:
        return self._id

    def get_process_pipeline_section_id(self) -> ProcessPipelineSectionId:
        return self._process_pipeline_section_id

    def get_constraint(self) -> Constraint:
        return self._constraint

    def get_pressure_control(self) -> PressureControlConfig:
        return self._pressure_control

    def get_anti_surge(self) -> AntiSurgeConfig:
        return self._anti_surge

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessProblemSectionId:
        return ProcessProblemSectionId(ecalc_id_generator())


class ProcessProblem(Entity[ProcessProblemId]):  # TODO: Rename to subproblem?
    def __init__(
        self,
        process_problem_sections: Sequence[ProcessProblemSection],
        configuration_handlers: Sequence[
            ConfigurationHandler
        ],  # inter or intra section config handlers, stored here for now
        process_pipeline_id: ProcessPipelineId,
        process_problem_id: ProcessProblemId | None = None,
    ):
        self._process_problem_sections = process_problem_sections
        self._configuration_handlers = configuration_handlers
        self._process_pipeline_id = process_pipeline_id
        self._id: Final[ProcessProblemId] = process_problem_id or ProcessProblem._create_id()

    def get_id(self) -> ProcessProblemId:
        return self._id

    def get_process_pipeline_id(self) -> ProcessPipelineId:
        return self._process_pipeline_id

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessProblemId:
        return ProcessProblemId(ecalc_id_generator())

    def get_process_problem_sections(self) -> Sequence[ProcessProblemSection]:
        return self._process_problem_sections

    def get_configuration_handlers(self) -> Sequence[ConfigurationHandler]:
        return self._configuration_handlers


ProcessSimulationId = NewType("ProcessSimulationId", UUID)


class ProcessSimulation(Entity[ProcessSimulationId]):  # process_model?
    def __init__(
        self,
        name: str,
        stream_distribution: CommonStreamDistributionConfig | IndividualStreamDistributionConfig,
        process_problems: list[ProcessProblem],
        process_periods: list[Period],
        process_simulation_id: ProcessSimulationId | None = None,
        process_configurations: dict[
            ProcessPipelineId,
            dict[
                ProcessUnitId,
                TimeSeriesTemperatureSetterConfiguration
                | TimeSeriesPressureDropperConfiguration
                | TimeSeriesSplitterConfiguration
                | TimeSeriesMixerConfiguration,
            ],
        ]
        | None = None,
    ):
        self._name = name
        self.stream_distribution = stream_distribution
        self.process_problems = process_problems
        self.process_periods = process_periods
        self.process_configurations = process_configurations
        self._id: Final[ProcessSimulationId] = process_simulation_id or ProcessSimulation._create_id()

    def get_id(self) -> ProcessSimulationId:
        return self._id

    def get_process_periods(self) -> list[Period]:
        """
        Get the global period vector - where START, END is taken into account, all temporal events (in legacy YAML) and relevant timeseries.
        Returns:

        """
        return self.process_periods

    def get_name(self) -> str:
        return self._name

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessSimulationId:
        return ProcessSimulationId(ecalc_id_generator())

    def get_inlet_streams(self) -> list[TimeSeriesStream]:
        match self.stream_distribution:
            case CommonStreamDistributionConfig():
                return [self.stream_distribution.inlet_stream]
            case IndividualStreamDistributionConfig():
                return self.stream_distribution.inlet_streams
            case _:
                assert_never(self.stream_distribution)
