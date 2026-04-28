from dataclasses import dataclass
from typing import Final, Literal, NewType, Self, assert_never
from uuid import UUID

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.domain.process.stream_distribution.common_stream_distribution import Overflow
from libecalc.domain.process.value_objects.fluid_stream.time_series_stream import TimeSeriesStream
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass
class CommonStreamSettings:
    rate_fractions: list[TimeSeriesExpression]
    overflow: list[Overflow]


@dataclass
class CommonStreamDistributionConfig:  # TODO: Rather a strategy that splits a stream in a method according to a policy?
    inlet_stream: TimeSeriesStream
    settings: list[CommonStreamSettings]


@dataclass
class IndividualStreamDistributionConfig:
    inlet_streams: list[TimeSeriesStream]


@dataclass
class Constraint:  # should this instead be more flexible wrt. matching one or more stream conditions?
    outlet_pressure: TimeSeriesExpression


@dataclass
class PressureControlConfig:  # Spec
    type: Literal["UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE", "COMMON_ASV", "INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE"]


@dataclass
class AntiSurgeConfig:
    type: Literal["INDIVIDUAL_ASV", "COMMON_ASV"]


ProcessProblemId = NewType("ProcessProblemId", UUID)


class ProcessProblem(Entity[ProcessProblemId]):  # TODO: Rename to subproblem?
    # can a problem exist wo. a simulation? yes, e.g. get max rate ...
    # given a physical pipeline (a contained problem, such as a compressor train), the user needs to define strategies to find a solution for the sub problem
    # TODO: might have subproblems, or dependencies, but we may want to add those as problems that depend on each other and needs to be evaluated in a given order

    def __init__(
        self,
        pressure_control_strategy: PressureControlConfig,
        anti_surge_strategy: AntiSurgeConfig,
        constraint: Constraint,
        process_pipeline_id: ProcessPipelineId,
        process_problem_id: ProcessProblemId | None = None,
    ):
        self.pressure_control_strategy = pressure_control_strategy
        self.anti_surge_strategy = anti_surge_strategy
        self.constraint = constraint
        self.process_pipeline_id = process_pipeline_id
        self._id: Final[ProcessProblemId] = process_problem_id or ProcessProblem._create_id()

    def get_id(self) -> ProcessProblemId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessProblemId:
        return ProcessProblemId(ecalc_id_generator())

    def get_constraint(self) -> Constraint:
        return self.constraint

    def get_pressure_control_strategy(self) -> PressureControlConfig:
        return self.pressure_control_strategy

    def get_anti_surge_strategy(self) -> AntiSurgeConfig:
        return self.anti_surge_strategy


ProcessSimulationId = NewType("ProcessSimulationId", UUID)


class ProcessSimulation(Entity[ProcessSimulationId]):  # process_model?
    """
    TODO: one or more subproblems, where we first need to find the stream distribution before looking at each subproblem separately
    quit and notify as soon as we notice we are not able to find a solution, or always finish?
    """

    def __init__(
        self,
        stream_distribution: CommonStreamDistributionConfig | IndividualStreamDistributionConfig,
        process_problems: list[ProcessProblem],
        process_simulation_id: ProcessSimulationId | None = None,
    ):
        self.stream_distribution = stream_distribution
        self.process_problems = process_problems
        self._id: Final[ProcessSimulationId] = process_simulation_id or ProcessSimulation._create_id()

    def get_id(self) -> ProcessSimulationId:
        return self._id

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
