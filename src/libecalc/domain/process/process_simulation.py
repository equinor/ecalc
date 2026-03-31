from dataclasses import dataclass
from typing import Literal

from libecalc.domain.process.process_system.process_system import ProcessSystem, ProcessSystemId
from libecalc.domain.process.stream_distribution.common_stream_distribution import Overflow
from libecalc.domain.process.value_objects.fluid_stream.time_series_stream import TimeSeriesStream
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass
class CommonStreamSettings:
    rate_fractions: list[TimeSeriesExpression]
    overflow: list[Overflow]


@dataclass
class CommonStreamDistributionConfig:
    inlet_stream: TimeSeriesStream
    settings: list[CommonStreamSettings]


@dataclass
class IndividualStreamDistributionConfig:
    inlet_streams: list[TimeSeriesStream]


@dataclass
class Constraint:
    process_system_id: ProcessSystemId
    outlet_pressure: TimeSeriesExpression


@dataclass
class PressureControlConfig:
    process_system_id: ProcessSystemId
    type: Literal["UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE", "COMMON_ASV", "INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE"]


@dataclass
class AntiSurgeConfig:
    process_system_id: ProcessSystemId
    type: Literal["INDIVIDUAL_ASV", "COMMON_ASV"]


@dataclass
class ProcessSimulation:
    process_systems: list[ProcessSystem]
    pressure_control_strategies: list[PressureControlConfig]
    anti_surge_strategies: list[AntiSurgeConfig]
    constraints: list[Constraint]
    stream_distribution: IndividualStreamDistributionConfig | CommonStreamDistributionConfig
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.shaft.shaft import Shaft
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.process_system.stream_propagator import StreamPropagator
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import SimpleStream, FluidStream
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression

@dataclass
class Overflow:
    from_reference: str
    to_reference: str


@dataclass
class CommonStreamSettings:
    rate_fractions: list[TimeSeriesExpression]
    overflow: list[Overflow]


@dataclass
class CommonStreamDistributionConfig:  # TODO: Rather a strategy that splits a stream in a method according to a policy?
    inlet_stream: SimpleStream
    settings: list[CommonStreamSettings]


@dataclass
class IndividualStreamDistributionConfig:
    inlet_streams: list[SimpleStream]

@dataclass
class Constraint:
    outlet_pressure: float
#    outlet_pressure: TimeSeriesExpression  # TODO

@dataclass
class PressureControlConfig: # Spec
    type: Literal["UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE", "COMMON_ASV", "INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE"]

@dataclass
class AntiSurgeConfig:
    type: Literal["INDIVIDUAL_ASV", "COMMON_ASV"]

ProcessScenarioId = NewType("ProcessScenarioId", UUID)

def create_process_scenario_id() -> ProcessScenarioId:
    return ProcessScenarioId(uuid.uuid4())

@dataclass
class ProcessPipeline:  # or simulator?
    """
    A part of a process topology that is calculated independently
    container propagators - ie systems or units ...
    TODO: subpipelines?
    """
    id: UUID
    stream_propagators: list[StreamPropagator]

    def get_process_units(self) -> list[ProcessUnit]:
        process_units = []
        for stream_propagator in self.stream_propagators:
            match stream_propagator:
                case ProcessSystem():
                    process_units.extend(stream_propagator.get_process_units())
                case ProcessUnit():
                    process_units.append(stream_propagator)

        return process_units

    def get_process_systems(self) -> list[ProcessSystem]:
        process_systems = []
        for stream_propagator in self.stream_propagators:
            match stream_propagator:
                case ProcessSystem():
                    process_systems.append(stream_propagator)
                    process_systems.extend(stream_propagator.get_process_systems())
                case _:
                    ...

        return process_systems


    def get_shafts(self) -> set[Shaft]:
        shafts = set()
        for propagator in self.stream_propagators: # TODO: Currently not handling process systems ..
            if isinstance(propagator, Compressor):
                shaft = propagator.shaft
                if not shaft in shafts: # TODO: Make sure we test on entity here
                    shafts.add(shaft)
        return shafts

@dataclass
class ProcessScenario:  # scenario? job? Split a given scenario into smaller sims? each sim is a job that can be paralellized?
    # TODO: Rename to scenario
    pressure_control_strategy: PressureControlConfig
    anti_surge_strategy: AntiSurgeConfig
    constraint: Constraint  # ie target pressure - and intermediate pressures ...
    inlet_stream: SimpleStream | FluidStream
    #stream_distribution: IndividualStreamDistributionConfig | CommonStreamDistributionConfig  # the inlet stream is only indirectly a part of sim, through the strategy. It could be separate, where the strategy is just a policy how to distr it
    process_pipeline_id: UUID  # embedded ref here now for convenience, but not a part of this aggr, so FK/ID later
    id: ProcessScenarioId = field(default_factory=create_process_scenario_id)

    def get_id(self) -> ProcessScenarioId:
        return self.id

    def get_inlet_stream(self) -> SimpleStream | FluidStream:
        return self.inlet_stream

    def get_constraint(self) -> Constraint:
        return self.constraint

    def get_pressure_control_strategy(self) -> PressureControlConfig:
        return self.pressure_control_strategy

#    def get_stream_distribution_config(self) -> IndividualStreamDistributionConfig | CommonStreamDistributionConfig:
#        return self.stream_distribution

    def get_anti_surge_strategy(self) -> AntiSurgeConfig:
        return self.anti_surge_strategy


@dataclass
class ProcessProblem:  #
    """
    TODO: sub_problems? one config per subproblem?
    """
    id: UUID
    process_scenario: ProcessScenario

@dataclass
class ProcessSolution:
    id: UUID
    configuration: dict[UUID, dict[str, float]]  #ProcessConfiguration later, just a very simple dict now. Possibly separate AggrRoot, but more like if we want to keep candidates, or we have to pick one from several solutions etc ...
    # keep config even when not success?
    success: bool
    reason: str

@dataclass
class ProcessSimulation:
    id: UUID
    process_problem_id: UUID
    process_solution_id: UUID
    outlet_stream: FluidStream