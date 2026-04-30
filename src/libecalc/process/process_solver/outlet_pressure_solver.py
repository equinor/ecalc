from collections.abc import Sequence
from typing import Final

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooLowError
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    RecirculationConfiguration,
    SpeedConfiguration,
)
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.process.process_solver.solver import Solution, SolverFailureStatus, TargetNotAchievableEvent
from libecalc.process.process_solver.solvers.speed_solver import SpeedSolver


class OutletPressureSolver:
    """Solver that finds the compressor speed, anti-surge recirculation, and
    pressure-control settings required to meet a target outlet pressure.

    The solver first searches for a shaft speed that produces the desired
    outlet pressure.  If the speed search cannot satisfy the constraint
    (e.g. because the target lies below the minimum-speed outlet pressure),
    it delegates to a PressureControlStrategy (upstream choke,
    downstream choke, ASV, etc.) to close the remaining gap.  Anti-surge
    protection is applied at every evaluation to keep compressor stages
    within their safe operating envelopes.
    """

    def __init__(
        self,
        shaft_id: ConfigurationHandlerId,
        process_pipeline_id: ProcessPipelineId,
        runner: ProcessRunner,
        anti_surge_strategy: AntiSurgeStrategy,
        pressure_control_strategy: PressureControlStrategy,
        root_finding_strategy: RootFindingStrategy,
        speed_boundary: Boundary,
    ) -> None:
        self._shaft_id: Final = shaft_id
        self._process_pipeline_id: Final = process_pipeline_id
        self._root_finding_strategy: Final = root_finding_strategy
        self._anti_surge_strategy: Final = anti_surge_strategy
        self._simulator: Final = runner
        self._pressure_control_strategy: Final = pressure_control_strategy
        self._speed_boundary: Final = speed_boundary

        self._anti_surge_solution: Solution[Sequence[Configuration[RecirculationConfiguration]]] | None = None

    @property
    def runner(self) -> ProcessRunner:
        return self._simulator

    @property
    def anti_surge_strategy(self) -> AntiSurgeStrategy:
        return self._anti_surge_strategy

    @property
    def pressure_control_strategy(self) -> PressureControlStrategy:
        return self._pressure_control_strategy

    @property
    def shaft_id(self) -> ConfigurationHandlerId:
        return self._shaft_id

    @property
    def process_pipeline_id(self) -> ProcessPipelineId:
        return self._process_pipeline_id

    def _get_initial_speed_boundary(self) -> Boundary:
        return self._speed_boundary

    def _find_speed_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[SpeedConfiguration]:
        speed_solver = SpeedSolver(
            search_strategy=BinarySearchStrategy(),
            root_finding_strategy=self._root_finding_strategy,
            boundary=self._get_initial_speed_boundary(),
            target_pressure=pressure_constraint.value,
        )

        def speed_func(configuration: SpeedConfiguration) -> FluidStream:
            self._simulator.reset_to(
                configurations=[Configuration(configuration_handler_id=self._shaft_id, value=configuration)],
            )
            try:
                return self._simulator.run(inlet_stream=inlet_stream)
            except RateTooLowError:
                solution = self._anti_surge_strategy.apply(inlet_stream=inlet_stream)
                self._simulator.apply_configurations(solution.configuration)
                return self._simulator.run(inlet_stream=inlet_stream)

        speed_solution = speed_solver.solve(speed_func)

        return speed_solution

    def _get_outlet_stream(self, inlet_stream: FluidStream, configurations: Sequence[Configuration]):
        self._simulator.apply_configurations(configurations)
        return self._simulator.run(inlet_stream=inlet_stream)

    def get_anti_surge_solution(self) -> Solution[Sequence[Configuration[RecirculationConfiguration]]]:
        assert self._anti_surge_solution is not None
        return self._anti_surge_solution

    def find_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]:
        """
        Finds the speed and recirculation rates for each compressor to meet the pressure constraint.
        """
        self._simulator.reset_to()
        configurations: dict[ConfigurationHandlerId, Configuration] = {}
        speed_solution = self._find_speed_solution(pressure_constraint=pressure_constraint, inlet_stream=inlet_stream)
        configurations[self._shaft_id] = Configuration(
            configuration_handler_id=self._shaft_id,
            value=speed_solution.configuration,
        )

        self._simulator.reset_to(configurations=list(configurations.values()))
        self._anti_surge_solution = self._anti_surge_strategy.apply(inlet_stream=inlet_stream)
        for anti_surge_configuration in self._anti_surge_solution.configuration:
            configurations[anti_surge_configuration.configuration_handler_id] = anti_surge_configuration

        if speed_solution.success:
            return Solution(
                success=True,
                configuration=list(configurations.values()),
            )

        if not self._anti_surge_solution.success:
            return Solution(
                success=False,
                configuration=list(configurations.values()),
                failure_event=self._anti_surge_solution.failure_event,
            )

        outlet_at_chosen_speed = self._get_outlet_stream(
            inlet_stream=inlet_stream,
            configurations=list(configurations.values()),
        )

        if outlet_at_chosen_speed.pressure_bara < pressure_constraint:
            return Solution(
                success=False,
                configuration=list(configurations.values()),
                failure_event=TargetNotAchievableEvent(
                    status=SolverFailureStatus.MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET,
                    achievable_value=outlet_at_chosen_speed.pressure_bara,
                    target_value=pressure_constraint.value,
                    source_id=self._process_pipeline_id,
                ),
            )

        pressure_control_solution = self._pressure_control_strategy.apply(
            target_pressure=pressure_constraint,
            inlet_stream=inlet_stream,
        )

        for pressure_control_configuration in pressure_control_solution.configuration:
            configurations[pressure_control_configuration.configuration_handler_id] = pressure_control_configuration

        failure_event = pressure_control_solution.failure_event
        if isinstance(failure_event, TargetNotAchievableEvent) and failure_event.source_id is None:
            failure_event = failure_event.with_source_id(self._process_pipeline_id)

        return Solution(
            success=pressure_control_solution.success,
            configuration=list(configurations.values()),
            failure_event=failure_event,
        )
