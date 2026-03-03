from collections.abc import Callable

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.candidate_evaluator import CandidateEvaluator
from libecalc.domain.process.process_solver.pressure_control.policies import CapacityPolicy, PressureControlPolicy
from libecalc.domain.process.process_solver.pressure_control.types import PressureControlConfiguration
from libecalc.domain.process.process_solver.search_strategies import RootFindingStrategy, SearchStrategy
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration, SpeedSolver
from libecalc.domain.process.process_system.process_error import OutsideCapacityError, ProcessError
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class PressureControlSolver:
    """
    Orchestrates pressure control for a compressor train.

    The solver uses speed as the outer degree of freedom to reach a target outlet pressure.

    Solving is performed in two stages:
      1) Apply the capacity policy as needed to obtain feasible evaluations while selecting speed.
         Speed selection is done by root finding on (outlet_pressure(speed) - target_pressure) using baseline evaluations.
      2) Apply the pressure control policy (ASV/choke) once at the selected speed - to meet target pressure if needed.

    `candidate_evaluator` applies a configuration to the underlying (mutable) system and propagates the inlet stream.
    """

    def __init__(
        self,
        *,
        speed_boundary: Boundary,
        search_strategy: SearchStrategy,
        root_finding_strategy: RootFindingStrategy,
        capacity_policy: CapacityPolicy,
        pressure_control_policy: PressureControlPolicy,
        candidate_evaluator: CandidateEvaluator,
    ):
        self._speed_boundary = speed_boundary
        self._search_strategy = search_strategy
        self._root_finding_strategy = root_finding_strategy
        self._capacity_policy = capacity_policy
        self._pressure_control_policy = pressure_control_policy
        self._candidate_evaluator = candidate_evaluator

    @staticmethod
    def _initial_cfg_for_speed(speed: float) -> PressureControlConfiguration:
        return PressureControlConfiguration(
            speed=speed,
            recirculation_rate=0.0,
            upstream_delta_pressure=0.0,
            downstream_delta_pressure=0.0,
        )

    def _apply_capacity(
        self,
        *,
        input_cfg: PressureControlConfiguration,
        evaluate_system: Callable[[PressureControlConfiguration], FluidStream],
    ) -> PressureControlConfiguration:
        """
        Apply the capacity policy to obtain a feasible configuration for evaluation.

        Raises:
            OutsideCapacityError: If no feasible configuration can be found within the policy's boundaries.
        """

        capacity_solution = self._capacity_policy.apply(
            input_cfg=input_cfg,
            evaluate_system=evaluate_system,
        )
        if not capacity_solution.success:
            raise OutsideCapacityError()
        return capacity_solution.configuration

    @staticmethod
    def _meets_target(outlet: FluidStream, target_pressure: FloatConstraint) -> bool:
        return abs(outlet.pressure_bara - target_pressure.value) <= target_pressure.abs_tol

    def solve(
        self,
        *,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[PressureControlConfiguration]:
        """
        Solve outlet-pressure control in two stages:

          A) Select speed using baseline evaluation with capacity handling only.
          B) Apply pressure control (ASV/choke) once at the selected speed.
        """

        def evaluate_cfg(cfg: PressureControlConfiguration) -> FluidStream:
            return self._candidate_evaluator.evaluate_candidate(cfg, inlet_stream=inlet_stream)

        def apply_capacity_at_speed(speed: float) -> PressureControlConfiguration:
            return self._apply_capacity(
                input_cfg=self._initial_cfg_for_speed(speed),
                evaluate_system=evaluate_cfg,
            )

        # -----------------------
        # Step A: solve for speed
        # -----------------------
        speed_solver = SpeedSolver(
            search_strategy=self._search_strategy,
            root_finding_strategy=self._root_finding_strategy,
            boundary=self._speed_boundary,
            target_pressure=target_pressure.value,
        )

        def speed_func(config: SpeedConfiguration) -> FluidStream:
            # Capacity only: do not apply pressure control while selecting speed.
            cfg = apply_capacity_at_speed(config.speed)
            return evaluate_cfg(cfg)

        speed_solution = speed_solver.solve(speed_func)
        chosen_speed = speed_solution.configuration.speed

        # -----------------------
        # Step B: final control
        # -----------------------
        try:
            feasible_cfg = apply_capacity_at_speed(chosen_speed)

            outlet_at_baseline = evaluate_cfg(feasible_cfg)
            if self._meets_target(outlet_at_baseline, target_pressure):
                return Solution(success=speed_solution.success, configuration=feasible_cfg)

            # Final pressure control at fixed speed.
            controlled_solution, outlet = self._pressure_control_policy.apply(
                input_cfg=feasible_cfg,
                target_pressure=target_pressure,
                evaluate_system=evaluate_cfg,
            )

            final_cfg = controlled_solution.configuration
            success = speed_solution.success and self._meets_target(outlet, target_pressure)
            return Solution(success=success, configuration=final_cfg)

        except ProcessError:
            return Solution(
                success=False,
                configuration=PressureControlConfiguration(speed=chosen_speed),
            )
