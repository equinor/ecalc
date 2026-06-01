from collections.abc import Sequence
from typing import Final

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    RecirculationConfiguration,
)
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.minimum_flow_protected_process_runner import (
    MinimumFlowProtectedProcessRunner,
)
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.solver import (
    RateTooHighFailure,
    Solution,
    TargetDirection,
    TargetPressureUnreachableFailure,
)
from libecalc.process.process_solver.speed_search import SpeedSearch


class OutletPressureSolver:
    """Solver that finds the compressor speed, anti-surge recirculation, and
    pressure-control settings required to meet a target outlet pressure.

    The solver first searches for a shaft speed that produces the desired
    outlet pressure.  If the speed search cannot satisfy the constraint
    (e.g. because the target lies below the minimum-speed outlet pressure),
    it delegates to a PressureControlStrategy (upstream choke,
    downstream choke, ASV, etc.) to close the remaining gap.  Anti-surge
    protection is provided by the protected runner, which transparently
    applies recirculation whenever a stage falls below minimum flow.
    """

    def __init__(
        self,
        shaft_id: ConfigurationHandlerId,
        process_pipeline_id: ProcessPipelineId,
        runner: MinimumFlowProtectedProcessRunner,
        pressure_control_strategy: PressureControlStrategy,
        speed_search: SpeedSearch,
    ) -> None:
        self._shaft_id: Final = shaft_id
        self._process_pipeline_id: Final = process_pipeline_id
        self._simulator: Final = runner
        self._pressure_control_strategy: Final = pressure_control_strategy
        self._speed_search: Final = speed_search

        self._anti_surge_solution: Solution[Sequence[Configuration[RecirculationConfiguration]]] | None = None

    @property
    def runner(self) -> MinimumFlowProtectedProcessRunner:
        return self._simulator

    @property
    def pressure_control_strategy(self) -> PressureControlStrategy:
        return self._pressure_control_strategy

    @property
    def shaft_id(self) -> ConfigurationHandlerId:
        return self._shaft_id

    @property
    def process_pipeline_id(self) -> ProcessPipelineId:
        return self._process_pipeline_id

    def get_anti_surge_solution(self) -> Solution[Sequence[Configuration[RecirculationConfiguration]]] | None:
        return self._anti_surge_solution

    def find_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]:
        """Finds the speed and recirculation rates for each compressor to meet the pressure constraint."""
        self._simulator.reset_to()
        configurations: dict[ConfigurationHandlerId, Configuration] = {}

        speed_solution = self._speed_search.find_speed(target_pressure=pressure_constraint, inlet_stream=inlet_stream)
        configurations[self._shaft_id] = Configuration(
            configuration_handler_id=self._shaft_id,
            value=speed_solution.configuration,
        )

        # Short-circuit: if rate exceeds compressor capacity at all speeds, anti-surge cannot help
        if isinstance(speed_solution.failure, RateTooHighFailure):
            return Solution(
                success=False,
                configuration=list(configurations.values()),
                failure=speed_solution.failure,
            )

        self._simulator.reset_to(configurations=list(configurations.values()))
        outlet_at_chosen_speed = self._simulator.run(inlet_stream=inlet_stream)
        self._anti_surge_solution = self._simulator.get_last_protection()
        if self._anti_surge_solution is not None:
            configurations.update({c.configuration_handler_id: c for c in self._anti_surge_solution.configuration})

        if speed_solution.success:
            return Solution(
                success=True,
                configuration=list(configurations.values()),
            )

        if self._anti_surge_solution is not None and not self._anti_surge_solution.success:
            return Solution(
                success=False,
                configuration=list(configurations.values()),
                failure=self._anti_surge_solution.failure,
            )

        if outlet_at_chosen_speed.pressure_bara < pressure_constraint:
            return Solution.target_pressure_unreachable(
                configuration=list(configurations.values()),
                achievable_pressure_bara=outlet_at_chosen_speed.pressure_bara,
                target_pressure_bara=pressure_constraint.value,
                source_id=self._process_pipeline_id,
                direction=TargetDirection.MAX_BELOW_TARGET,
            )

        pressure_control_solution = self._pressure_control_strategy.apply(
            target_pressure=pressure_constraint,
            inlet_stream=inlet_stream,
        )

        for pressure_control_configuration in pressure_control_solution.configuration:
            configurations[pressure_control_configuration.configuration_handler_id] = pressure_control_configuration

        failure = pressure_control_solution.failure
        if isinstance(failure, TargetPressureUnreachableFailure) and failure.source_id is None:
            failure = failure.with_source_id(self._process_pipeline_id)

        return Solution(
            success=pressure_control_solution.success,
            configuration=list(configurations.values()),
            failure=failure,
        )
