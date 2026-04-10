import uuid
from dataclasses import dataclass, field
from typing import Literal, NewType
from uuid import UUID

from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_system.process_system import ProcessSystem, ProcessSystemId
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.process_system.stream_propagator import StreamPropagator
from libecalc.domain.process.stream_distribution.common_stream_distribution import Overflow
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import SimpleStream
from libecalc.domain.process.value_objects.fluid_stream.time_series_stream import TimeSeriesStream
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass
class CommonStreamSettings:
    rate_fractions: list[str] #TimeSeriesExpression]
    overflow: list[Overflow]


@dataclass
class CommonStreamDistributionConfig:  # TODO: Rather a strategy that splits a stream in a method according to a policy?
    inlet_stream: SimpleStream # TimeseriesStream
    settings: list[CommonStreamSettings]


@dataclass
class IndividualStreamDistributionConfig:
    inlet_streams: list[SimpleStream] #TimeseriesStream

@dataclass
class Constraint:
    outlet_pressure: float # TimeSeriesExpression
    # process_system_id?

@dataclass
class PressureControlConfig: # Spec
    type: Literal["UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE", "COMMON_ASV", "INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE"]
    # process_system_id

@dataclass
class AntiSurgeConfig:
    type: Literal["INDIVIDUAL_ASV", "COMMON_ASV"]
    # process_system_id

ProcessScenarioId = NewType("ProcessScenarioId", UUID)

def create_process_scenario_id() -> ProcessScenarioId:
    return ProcessScenarioId(uuid.uuid4())

@dataclass
class ProcessPipeline:  # or simulator?
    """
    A part of a process topology that is calculated independently
    container propagators - ie systems or units ...

    the static physical stuff that we know a priori
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

    def get_process_systems(self) -> set[ProcessSystem]:
        process_systems = set()
        for stream_propagator in self.stream_propagators:
            match stream_propagator:
                case ProcessSystem():
                    process_systems.add(stream_propagator)
                    process_systems.update(stream_propagator.get_process_systems())

        return process_systems


    def get_process_system_unit_pairs(self) -> dict[ProcessUnitId | ProcessSystemId, ProcessSystemId]:
        process_system_unit_pairs = {}
        for stream_propagator in self.stream_propagators:
            match stream_propagator:
                case ProcessUnit():
                    ...
                case ProcessSystem():
                    process_system_unit_pairs.update(stream_propagator.get_process_system_unit_pairs())

        return process_system_unit_pairs

    def get_shafts(self) -> set[Shaft]:
        shafts = set()
        for propagator in self.stream_propagators: # TODO: Currently not handling process systems ..
            if isinstance(propagator, Compressor):
                shaft = propagator.shaft
                if not shaft in shafts: # TODO: Make sure we test on entity here
                    shafts.add(shaft)
        return shafts

@dataclass
class ProcessScenario: # TODO: Rename to subproblem?
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
class ProcessSimulation: # process_model?
    """
    TODO: one or more subproblems, where we first need to find the stream distribution before looking at each subproblem separately
    quit and notify as soon as we notice we are not able to find a solution, or always finish?
    """
    id: UUID
    stream_distribution: IndividualStreamDistributionConfig | CommonStreamDistributionConfig  # the inlet stream is only indirectly a part of sim, through the strategy. It could be separate, where the strategy is just a policy how to distr it
    process_scenarios: list[ProcessScenario]  # todo: subproblem? TODO: a part of aggr or not?

    def get_stream_distribution_config(self) -> IndividualStreamDistributionConfig | CommonStreamDistributionConfig:
        return self.stream_distribution

"""@dataclass
class ProcessSimulation:
    process_systems: list[ProcessSystem]
    pressure_control_strategies: list[PressureControlConfig]
    anti_surge_strategies: list[AntiSurgeConfig]
    constraints: list[Constraint]
    stream_distribution: IndividualStreamDistributionConfig | CommonStreamDistributionConfig
"""

"""
@dataclass
class ProcessSubSolution:
    id: UUID
    process_subproblem_id: UUID
    configuration: dict[UUID, dict[str, float]]

@dataclass
class ProcessSolution:
    #For a process problem, we have a stream distribution solution (or more?) along with configurations for each strategy
    id: UUID
    process_problem_id: UUID
    process_sub_solutions: ProcessSubSolution  # currently 1 solution, but may be more later ...
    #stream_distribution_configuration: StreamDistributionSolution
    #configuration: dict[UUID, dict[str, float]]  #ProcessConfiguration later, just a very simple dict now. Possibly separate AggrRoot, but more like if we want to keep candidates, or we have to pick one from several solutions etc ...
    # keep config even when not success?
    #success: bool
    #reason: str

# run in a solver, which is a domain service

@dataclass
class ProcessSimulation:
    #Once we have found all solutions, or just have a configuration that we want to simulate, we simulate it
    id: UUID
    process_problem_id: UUID
    process_solution_id: UUID
    outlet_stream: FluidStream
# TODO: The simulation is run in a runner or simulator, which is a domain service
"""