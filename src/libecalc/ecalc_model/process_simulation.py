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
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType
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
    pressure_control: PressureControlConfig
    anti_surge: AntiSurgeConfig
    target_process_unit_id: ProcessUnitId


ProcessProblemId = NewType("ProcessProblemId", UUID)


class ProcessProblem(Entity[ProcessProblemId]):  # TODO: Rename to subproblem?
    # can a problem exist wo. a simulation? yes, e.g. get max rate ...
    # given a physical pipeline (a contained problem, such as a compressor train), the user needs to define strategies to find a solution for the sub problem
    # TODO: might have subproblems, or dependencies, but we may want to add those as problems that depend on each other and needs to be evaluated in a given order

    def __init__(
        self,
        constraints: list[Constraint],
        configuration_handlers: Sequence[ConfigurationHandler],
        process_pipeline_id: ProcessPipelineId,
        process_problem_id: ProcessProblemId | None = None,
    ):
        self.constraints = constraints
        self.process_pipeline_id = process_pipeline_id
        self.configuration_handlers = configuration_handlers
        self._id: Final[ProcessProblemId] = process_problem_id or ProcessProblem._create_id()

    def get_id(self) -> ProcessProblemId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessProblemId:
        return ProcessProblemId(ecalc_id_generator())

    def get_constraints(self) -> list[Constraint]:
        return self.constraints


ProcessSimulationId = NewType("ProcessSimulationId", UUID)


class ProcessSimulation(Entity[ProcessSimulationId]):  # process_model?
    """
    TODO: one or more subproblems, where we first need to find the stream distribution before looking at each subproblem separately
    quit and notify as soon as we notice we are not able to find a solution, or always finish?
    """

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
