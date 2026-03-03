from abc import ABC, abstractmethod

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.pressure_control.types import (
    PressureControlConfiguration,
    RunPressureControlCfg,
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
    Capacity policy for compressor trains with individual anti-surge valves (ASV) per stage.

    Responsibility:
      - At fixed speed, adjust per-stage recirculation only as needed to obtain a feasible operating point
        (e.g. resolve minimum-flow violations), without attempting to meet the target outlet pressure.

    Requires:
      - PressureControlConfiguration must support per-stage recirculation (e.g. recirculation_rates_per_stage).
      - The underlying process model / configure_system must be able to apply per-stage recirculation settings.

    Not implemented yet.
    """

    def __init__(self, *args, **kwargs):
        pass

    def apply(
        self,
        *,
        input_cfg: "PressureControlConfiguration",
        run_system: RunPressureControlCfg,
    ) -> Solution["PressureControlConfiguration"]:
        raise NotImplementedError(
            "IndividualASVMinCapacityPolicy is not implemented. "
            "Implement per-stage capacity handling (minimum-flow) using cfg.recirculation_rates_per_stage and an "
            "adapter that can apply per-stage ASV settings."
        )
