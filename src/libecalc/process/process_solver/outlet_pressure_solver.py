from collections.abc import Sequence
from typing import Final

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_solver.configuration import (
    Configuration,
    RecirculationConfiguration,
)
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.solver import (
    Solution,
    TargetDirection,
    TargetPressureUnreachableFailure,
)
from libecalc.process.process_solver.speed_strategy.speed_strategy import SpeedStrategy, SpeedStrategySolution


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
        process_pipeline_id: ProcessPipelineId,
        runner: ProcessRunner,
        pressure_control_strategy: PressureControlStrategy,
        speed_strategy: SpeedStrategy,
    ) -> None:
        self._process_pipeline_id: Final = process_pipeline_id
        self._simulator: Final = runner
        self._pressure_control_strategy: Final = pressure_control_strategy
        self._speed_solution: SpeedStrategySolution | None = None
        self._speed_strategy: Final = speed_strategy

    @property
    def runner(self) -> ProcessRunner:
        return self._simulator

    @property
    def pressure_control_strategy(self) -> PressureControlStrategy:
        return self._pressure_control_strategy

    @property
    def process_pipeline_id(self) -> ProcessPipelineId:
        return self._process_pipeline_id

    @property
    def speed_strategy(self):
        return self._speed_strategy

    def _get_outlet_stream(self, inlet_stream: FluidStream, configurations: Sequence[Configuration]):
        self._simulator.apply_configurations(configurations)
        return self._simulator.run(inlet_stream=inlet_stream)

    def get_anti_surge_solution(self) -> Solution[Sequence[Configuration[RecirculationConfiguration]]] | None:
        if self._speed_solution is None:
            return None
        return self._speed_solution.get_anti_surge_solution()

    def find_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]:
        """
        Finds the speed and recirculation rates for each compressor to meet the pressure constraint.
        """
        self._simulator.reset_to()
        speed_solution = self._speed_strategy.apply(target_pressure=pressure_constraint, inlet_stream=inlet_stream)
        self._speed_solution = speed_solution

        anti_surge_solution = speed_solution.get_anti_surge_solution()

        if speed_solution.is_success():
            # Pressure is met
            return Solution(
                success=True,
                configuration=speed_solution.get_configurations(),
            )
        elif anti_surge_solution is None or not anti_surge_solution.success:
            # Anti surge does not consider target pressure, if no solution found we are unable to propagate stream at all
            return Solution(
                success=False,
                configuration=speed_solution.get_configurations(),
                failure=speed_solution.get_failures()[-1],
            )

        outlet_at_chosen_speed = self._get_outlet_stream(
            inlet_stream=inlet_stream,
            configurations=speed_solution.get_configurations(),
        )

        if outlet_at_chosen_speed.pressure_bara < pressure_constraint:
            return Solution.target_pressure_unreachable(
                configuration=speed_solution.get_configurations(),
                achievable_pressure_bara=outlet_at_chosen_speed.pressure_bara,
                target_pressure_bara=pressure_constraint.value,
                source_id=self._process_pipeline_id,
                direction=TargetDirection.MAX_BELOW_TARGET,
            )

        pressure_control_solution = self._pressure_control_strategy.apply(
            target_pressure=pressure_constraint,
            inlet_stream=inlet_stream,
        )

        # Speed strategy (anti-surge) and pressure control might configure the same units, overwrite with pressure control configs.
        configurations = {config.configuration_handler_id: config for config in speed_solution.get_configurations()}
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
