from collections.abc import Callable

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
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
    For each speed evaluation it applies:
      1) A capacity policy (optional): bring the operating point within capacity (e.g. via minimum recirculation).
      2) A pressure control policy: adjust ASV/choke to meet the target outlet pressure at that speed.

    `evaluate_system` is injected as a callback and is responsible for:
      - applying speed/recirculation/choke to the underlying process model, and
      - propagating the system for the intended inlet stream.
    """

    def __init__(
        self,
        *,
        speed_boundary: Boundary,
        search_strategy: SearchStrategy,
        root_finding_strategy: RootFindingStrategy,
        capacity_policy: CapacityPolicy,
        pressure_control_policy: PressureControlPolicy,
    ):
        self._speed_boundary = speed_boundary
        self._search_strategy = search_strategy
        self._root_finding_strategy = root_finding_strategy
        self._capacity_policy = capacity_policy
        self._pressure_control_policy = pressure_control_policy

    def solve(
        self,
        *,
        target_pressure: FloatConstraint,
        evaluate_system: Callable[[PressureControlConfiguration], FluidStream],
    ) -> Solution[PressureControlConfiguration]:
        """
        Notes / design intent:
          - Keep pressure-control (ASV/choke) out of the speed loop: SpeedSolver needs outlet pressure to vary with speed.
            If we also adjust ASV/choke while evaluating each speed, many speeds may appear to "hit the target",
            and the chosen speed (and resulting recirculation) can become unstable/non-deterministic.
          - Therefore we split solving into two stages: (A) pick speed using capacity handling only,
            then (B) apply the pressure-control policy once at the selected speed.

        Two-stage solve:

        Step A (speed solve):
          - Find a speed that can meet the target pressure, using only capacity handling to ensure feasibility.
          - Do NOT run pressure-control (ASV/choke) inside the speed loop. This avoids degenerating the speed signal.

        Step B (final control at chosen speed):
          - Apply capacity policy once more at the chosen speed.
          - Apply pressure-control policy (ASV/choke) at fixed speed to hit the target.
            (Policies are expected to behave as no-ops when the baseline configuration already meets the target,
            e.g. choke policies that do nothing when outlet pressure is below target.)
        """

        def apply_capacity_at_speed(speed: float) -> PressureControlConfiguration:
            """Return a feasible configuration at given speed (or raise OutsideCapacityError)."""
            initial_cfg = PressureControlConfiguration(speed=speed)

            capacity_solution = self._capacity_policy.apply(
                input_cfg=initial_cfg,
                evaluate_system=evaluate_system,
            )

            if not capacity_solution.success:
                # No feasible point at this speed within configured boundaries
                # We raise to let SpeedSolver treat this as an unusable speed (best-effort handling is in SpeedSolver).
                raise OutsideCapacityError()

            return capacity_solution.configuration

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
            # Only ensure feasibility (capacity). Do not do pressure control here.
            # Important: capacity_policy may add recirculation to get within min-flow, but it must not try to
            # "hit target pressure". That would remove the pressure-vs-speed signal needed by SpeedSolver.
            cfg = apply_capacity_at_speed(config.speed)
            return evaluate_system(cfg)

        speed_solution = speed_solver.solve(speed_func)

        # Best effort: always attempt to produce a complete configuration at the selected speed.
        chosen_speed = speed_solution.configuration.speed

        # -------------------------------
        # Step B: final control at chosen speed
        # - Apply capacity policy once more at the chosen speed.
        # - If baseline already meets target, return it. Otherwise, apply pressure-control policy (ASV/choke) at fixed speed.
        # -------------------------------
        try:
            # Re-apply capacity at the chosen speed to produce a feasible baseline for the pressure-control policy.
            feasible_cfg = apply_capacity_at_speed(chosen_speed)

            # Short-circuit: if we already meet the target at the feasible baseline configuration,
            # avoid running the pressure-control policy (which may trigger additional root-finding/evaluations).
            #
            # This also makes Step B consistent with the semantics of "pressure control" (only adjust ASV/choke when needed).
            outlet_at_baseline = evaluate_system(feasible_cfg)
            meets_target_at_baseline = (
                abs(outlet_at_baseline.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
            )

            if meets_target_at_baseline:
                return Solution(success=speed_solution.success, configuration=feasible_cfg)

            controlled_solution, outlet = self._pressure_control_policy.apply(
                input_cfg=feasible_cfg,
                target_pressure=target_pressure,
                evaluate_system=evaluate_system,
            )

            final_cfg = controlled_solution.configuration
            meets_target = abs(outlet.pressure_bara - target_pressure.value) <= target_pressure.abs_tol

            # Overall success requires:
            # - speed loop succeeded AND
            # - final configuration meets target (pressure policy may be best-effort)
            success = speed_solution.success and meets_target
            return Solution(success=success, configuration=final_cfg)

        except ProcessError:
            # If even best-effort evaluation fails at that speed, fall back to minimal config.
            # (I.e. still return the chosen speed so callers can see what was attempted.)
            return Solution(
                success=False,
                configuration=PressureControlConfiguration(speed=chosen_speed),
            )
