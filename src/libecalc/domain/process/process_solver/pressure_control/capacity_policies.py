from abc import ABC, abstractmethod
from collections.abc import Callable

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.pressure_control.types import (
    PressureControlConfiguration,
    RunPressureControlCfg,
    RunStage,
)
from libecalc.domain.process.process_solver.pressure_control.utils import create_recirculation_eval_func
from libecalc.domain.process.process_solver.search_strategies import RootFindingStrategy, SearchStrategy
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationSolver
from libecalc.domain.process.process_system.process_error import RateTooLowError


# -------------------------
# Capacity policy interface
# -------------------------
class CapacityPolicy(ABC):
    """
    Adjust configuration at fixed speed to get within compressor capacity.

    This is intended to handle chart violations such as `RateTooLowError`.
    It does not attempt to meet the target outlet pressure.

    `Solution.success=True` means the returned configuration evaluates without capacity-related errors.
    """

    @abstractmethod
    def apply(
        self,
        *,
        input_cfg: PressureControlConfiguration,
        run_system: RunPressureControlCfg,
    ) -> Solution[PressureControlConfiguration]: ...


# ---------------------------------------
# Implementations of capacity policies
# ---------------------------------------
class NoCapacityPolicy(CapacityPolicy):
    """No capacity handling. Returns the input configuration unchanged."""

    def apply(
        self,
        *,
        input_cfg: PressureControlConfiguration,
        run_system: RunPressureControlCfg,
    ) -> Solution[PressureControlConfiguration]:
        return Solution(success=True, configuration=input_cfg)


class CommonASVMinFlowPolicy(CapacityPolicy):
    """
    Capacity policy that resolves `RateTooLowError` by increasing recirculation to minimum feasible.

    Implementation detail:
      - Tries the baseline configuration first.
      - If `RateTooLowError`, uses `RecirculationSolver(target_pressure=None)` to find the minimum recirculation rate
        that becomes feasible within the configured boundary.
    """

    def __init__(
        self,
        *,
        recirculation_rate_boundary: Boundary,
        search_strategy: SearchStrategy,
        root_finding_strategy: RootFindingStrategy,
    ):
        self._recirculation_boundary = recirculation_rate_boundary
        self._search_strategy = search_strategy
        self._root_finding_strategy = root_finding_strategy

    def apply(
        self,
        *,
        input_cfg: PressureControlConfiguration,
        run_system: RunPressureControlCfg,
    ) -> Solution[PressureControlConfiguration]:
        baseline_cfg = input_cfg

        # Step 0: Try without changing anything. If it evaluates, we are already within capacity.
        try:
            run_system(baseline_cfg)
            return Solution(success=True, configuration=baseline_cfg)

        # Step 1: If we are below minimum flow, try to "fix capacity" by increasing recirculation.
        except RateTooLowError:
            recirculation_solver = RecirculationSolver(
                search_strategy=self._search_strategy,
                root_finding_strategy=self._root_finding_strategy,
                recirculation_rate_boundary=self._recirculation_boundary,
                target_pressure=None,  # capacity only
            )

            # Only recirculation_rate varies. Everything else (speed/chokes) stays as in baseline_cfg.
            recirculation_func = create_recirculation_eval_func(
                baseline_cfg=baseline_cfg,
                run_system=run_system,
            )

            recirculation_solution = recirculation_solver.solve(recirculation_func)

            # Build the candidate configuration we intend to use going forward.
            capacity_cfg = PressureControlConfiguration(
                speed=baseline_cfg.speed,
                recirculation_rate=recirculation_solution.configuration.recirculation_rate,
                upstream_delta_pressure=baseline_cfg.upstream_delta_pressure,
                downstream_delta_pressure=baseline_cfg.downstream_delta_pressure,
            )

            # Step 2: If the solver could not find any feasible point within the recirculation boundary,
            # we still return the "best effort" config, but with success=False.
            if not recirculation_solution.success:
                return Solution(success=False, configuration=capacity_cfg)

            # Step 3: Optional safety check: verify that the returned config is actually feasible.
            # This makes success=True mean "this configuration evaluates without capacity errors".
            try:
                run_system(capacity_cfg)
            except RateTooLowError:
                return Solution(success=False, configuration=capacity_cfg)

            return Solution(success=True, configuration=capacity_cfg)


class IndividualASVMinFlowPolicy(CapacityPolicy):
    """
    Implements capacity control for INDIVIDUAL_ASV_PRESSURE and INDIVIDUAL_ASV_RATE.

    Ensures each stage operates at or above its minimum flow by setting the minimum
    required recirculation rate per stage independently.

    Used as a pre-step before pressure control: brings all stages inside capacity
    before any pressure target is attempted.

    The caller must build run_stage_fns such that run_stage_fns[i]:
    - accepts a recirculation rate [Sm3/day] and returns the outlet FluidStream
    - closes over its RecirculationLoop and the inlet stream for that stage

    The caller must build min_recirculation_rate_fns such that min_recirculation_rate_fns[i]:
    - returns the minimum recirculation rate [Sm3/day] needed to bring stage i inside capacity
    - closes over the compressor stage and its current inlet stream
    """

    def __init__(
        self,
        *,
        run_stage_fns: list[RunStage],
        min_recirculation_rate_fns: list[Callable[[], float]],  # closes over inlet stream per stage
    ):
        self._run_stage_fns = run_stage_fns
        self._min_recirculation_rate_fns = min_recirculation_rate_fns

    def apply(
        self,
        *,
        input_cfg: PressureControlConfiguration,
        run_system: RunPressureControlCfg,
    ) -> Solution[PressureControlConfiguration]:
        # Set minimum recirculation rate per stage to bring all stages inside capacity.
        # Outlet of stage i becomes inlet for stage i+1 via the closed-over run_stage_fns.
        rates = []
        for run_stage, min_rate_fn in zip(self._run_stage_fns, self._min_recirculation_rate_fns):
            min_rate = min_rate_fn()  # inlet stream is closed over by the caller
            rates.append(min_rate)
            run_stage(min_rate)  # propagate to update state for next stage

        cfg = PressureControlConfiguration(
            speed=input_cfg.speed,
            recirculation_rates_per_stage=tuple(rates),
        )
        return Solution(success=True, configuration=cfg)
