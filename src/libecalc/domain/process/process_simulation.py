import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, NewType
from uuid import UUID

from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.process_system.stream_propagator import StreamPropagator
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


ProcessScenarioId = NewType("ProcessScenarioId", UUID)


def create_process_scenario_id() -> ProcessScenarioId:
    return ProcessScenarioId(uuid.uuid4())


ProcessPipelineId = NewType("ProcessPipelineId", UUID)


def create_process_pipeline_id() -> ProcessPipelineId:
    return ProcessPipelineId(uuid.uuid4())


@dataclass
class ProcessPipeline:  # or simulator?
    """
    A part of a process topology that is calculated independently
    container propagators - ie systems or units ...

    the static physical stuff that we know a priori
    TODO: subpipelines?
    """

    id: ProcessPipelineId
    stream_propagators: Sequence[StreamPropagator]

    def get_process_units(self) -> list[ProcessUnit]:
        process_units = []
        for stream_propagator in self.stream_propagators:
            match stream_propagator:
                case ProcessSystem():
                    process_units.extend(stream_propagator.get_process_units())
                case ProcessUnit():
                    process_units.append(stream_propagator)

        return process_units


@dataclass
class ProcessScenario:  # TODO: Rename to subproblem?
    # can a scenario exist wo. a simulation? yes, e.g. get max rate ...
    # given a physical pipeline (a confined problem, such as a compressor train), the user needs to define strategies to find a solution for the sub problem
    pressure_control_strategy: PressureControlConfig
    anti_surge_strategy: AntiSurgeConfig
    constraint: Constraint  # ie target pressure - and intermediate pressures ...
    process_pipeline_id: UUID  # embedded ref here now for convenience, but not a part of this aggr, so FK/ID later
    id: ProcessScenarioId = field(default_factory=create_process_scenario_id)

    def get_id(self) -> ProcessScenarioId:
        return self.id

    def get_constraint(self) -> Constraint:
        return self.constraint

    def get_pressure_control_strategy(self) -> PressureControlConfig:
        return self.pressure_control_strategy

    def get_anti_surge_strategy(self) -> AntiSurgeConfig:
        return self.anti_surge_strategy


@dataclass
class ProcessSimulation:  # process_model?
    """
    TODO: one or more subproblems, where we first need to find the stream distribution before looking at each subproblem separately
    quit and notify as soon as we notice we are not able to find a solution, or always finish?
    """

    id: UUID
    stream_distribution: (
        IndividualStreamDistributionConfig | CommonStreamDistributionConfig
    )  # the inlet stream is only indirectly a part of sim, through the strategy. It could be separate, where the strategy is just a policy how to distr it
    process_scenarios: list[ProcessScenario]  # todo: subproblem? TODO: a part of aggr or not?

    def get_stream_distribution_config(self) -> IndividualStreamDistributionConfig | CommonStreamDistributionConfig:
        return self.stream_distribution
