from abc import ABC, abstractmethod
from collections.abc import Callable

from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.types import PressureControlConfiguration
from libecalc.domain.process.process_solver.search_strategies import RootFindingStrategy, SearchStrategy
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import (
    ChokeConfiguration,
    DownstreamChokeSolver,
)
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.process_solver.solvers.upstream_choke_solver import UpstreamChokeSolver
from libecalc.domain.process.process_system.process_error import RateTooLowError
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

RunPressureControlCfg = Callable[[PressureControlConfiguration], FluidStream]


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


# -------------------------------
# Pressure control policy interface
# -------------------------------
class PressureControlPolicy(ABC):
    """
    Apply pressure control at fixed speed to meet target outlet pressure.

    Assumes capacity has already been handled.
    """

    @abstractmethod
    def apply(
        self,
        *,
        input_cfg: PressureControlConfiguration,
        target_pressure: FloatConstraint,
        run_system: RunPressureControlCfg,
    ) -> tuple[Solution[PressureControlConfiguration], FluidStream]: ...


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


class CommonASVMinCapacityPolicy(CapacityPolicy):
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
            recirculation_func = _make_recirculation_eval_func(
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


class IndividualASVMinCapacityPolicy(CapacityPolicy):
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


# ---------------------------------------------
# Implementations of pressure control policies
# ---------------------------------------------
class NoPressureControlPolicy(PressureControlPolicy):
    """
    No pressure control. Evaluates the system as-is and returns the input configuration unchanged.

    success=True only if the unmodified configuration already meets the target pressure within abs_tol.
    """

    def apply(
        self,
        *,
        input_cfg: PressureControlConfiguration,
        target_pressure: FloatConstraint,
        run_system: RunPressureControlCfg,
    ) -> tuple[Solution[PressureControlConfiguration], FluidStream]:
        outlet = run_system(input_cfg)
        success = abs(outlet.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
        return Solution(success=success, configuration=input_cfg), outlet


class CommonASVPressureControlPolicy(PressureControlPolicy):
    """
    Pressure control using a common anti-surge recirculation loop (ASV) at fixed shaft speed.

    The policy varies `recirculation_rate` to meet the target outlet pressure within tolerance.
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
        target_pressure: FloatConstraint,
        run_system: RunPressureControlCfg,
    ) -> tuple[Solution[PressureControlConfiguration], FluidStream]:
        baseline_cfg = input_cfg

        recirculation_solver = RecirculationSolver(
            search_strategy=self._search_strategy,
            root_finding_strategy=self._root_finding_strategy,
            recirculation_rate_boundary=self._recirculation_boundary,
            target_pressure=target_pressure,
        )

        recirculation_func = _make_recirculation_eval_func(
            baseline_cfg=baseline_cfg,
            run_system=run_system,
        )

        # Vary only recirculation rate to meet target pressure at fixed speed.
        recirculation_solution = recirculation_solver.solve(recirculation_func)

        controlled_cfg = PressureControlConfiguration(
            speed=baseline_cfg.speed,
            recirculation_rate=recirculation_solution.configuration.recirculation_rate,
            upstream_delta_pressure=baseline_cfg.upstream_delta_pressure,
            downstream_delta_pressure=baseline_cfg.downstream_delta_pressure,
        )
        outlet_stream = run_system(controlled_cfg)

        meets_target = abs(outlet_stream.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
        success = recirculation_solution.success and meets_target
        return Solution(success=success, configuration=controlled_cfg), outlet_stream


class IndividualASVRatePressureControlPolicy(PressureControlPolicy):
    """
    Pressure control policy corresponding to legacy INDIVIDUAL_ASV_RATE.

    Responsibility:
      - At fixed speed, adjust individual ASVs (per stage) to meet the target outlet pressure.

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
        target_pressure: FloatConstraint,
        run_system: RunPressureControlCfg,
    ) -> tuple[Solution["PressureControlConfiguration"], FluidStream]:
        raise NotImplementedError(
            "IndividualASVRatePressureControlPolicy is not implemented. "
            "Implement legacy INDIVIDUAL_ASV_RATE behavior using per-stage ASV control and evaluate_system(cfg)."
        )


class IndividualASVPressureControlPolicy(PressureControlPolicy):
    """
    Pressure control policy corresponding to legacy INDIVIDUAL_ASV_PRESSURE.

    Responsibility:
      - At fixed speed, meet the target outlet pressure by distributing pressure ratio across stages and adjusting
        ASVs independently per stage.

    Requires:
      - Stage-level evaluation support (or evaluation results that expose per-stage outlet pressures), since the
        algorithm is inherently stage-by-stage.

    Not implemented yet.
    """

    def __init__(self, *args, **kwargs):
        pass

    def apply(
        self,
        *,
        input_cfg: "PressureControlConfiguration",
        target_pressure: FloatConstraint,
        run_system: RunPressureControlCfg,
    ) -> tuple[Solution["PressureControlConfiguration"], FluidStream]:
        raise NotImplementedError(
            "IndividualASVPressureControlPolicy is not implemented. "
            "Implement legacy INDIVIDUAL_ASV_PRESSURE behavior; this requires stage-level evaluation or evaluation "
            "results that expose per-stage pressures."
        )


class DownstreamChokePressureControlPolicy(PressureControlPolicy):
    """
    Pressure control policy using a downstream choke valve.

    The policy applies choking only when the unchoked outlet pressure is above target.

    Downstream means choking after the process system.

    When outlet is below target, choking is not applied and success will be False unless we are already within tolerance.
    """

    def apply(
        self,
        *,
        input_cfg: PressureControlConfiguration,
        target_pressure: FloatConstraint,
        run_system: RunPressureControlCfg,
    ) -> tuple[Solution[PressureControlConfiguration], FluidStream]:
        baseline_cfg = input_cfg
        outlet_stream_at_baseline = run_system(baseline_cfg)

        # Only choke when needed.
        if outlet_stream_at_baseline.pressure_bara <= target_pressure.value + EPSILON:
            # Already at/below target without choking => success (within tolerance check can be strict if you want)
            success = abs(outlet_stream_at_baseline.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
            return Solution(success=success, configuration=baseline_cfg), outlet_stream_at_baseline

        choke_solver = DownstreamChokeSolver(target_pressure=target_pressure.value)

        def outlet_with_downstream_choke(ccfg: ChokeConfiguration) -> FluidStream:
            candidate_cfg = PressureControlConfiguration(
                speed=baseline_cfg.speed,
                recirculation_rate=baseline_cfg.recirculation_rate,
                upstream_delta_pressure=baseline_cfg.upstream_delta_pressure,
                downstream_delta_pressure=ccfg.delta_pressure,
            )
            return run_system(candidate_cfg)

        choke_solution = choke_solver.solve(outlet_with_downstream_choke)

        controlled_cfg = PressureControlConfiguration(
            speed=baseline_cfg.speed,
            recirculation_rate=baseline_cfg.recirculation_rate,
            upstream_delta_pressure=baseline_cfg.upstream_delta_pressure,
            downstream_delta_pressure=choke_solution.configuration.delta_pressure,
        )

        outlet_stream = run_system(controlled_cfg)
        success = abs(outlet_stream.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
        return Solution(success=success, configuration=controlled_cfg), outlet_stream


class UpstreamChokePressureControlPolicy(PressureControlPolicy):
    """
    Pressure control policy using an upstream choke valve.

    Requires the evaluation function to interpret `upstream_delta_pressure` such that the compressor train sees
    reduced suction pressure.

    Upstream means choking before the process system, i.e. reducing inlet pressure to the compressor train.
    """

    def __init__(
        self,
        *,
        upstream_delta_pressure_boundary: Boundary,
        root_finding_strategy: RootFindingStrategy,
    ):
        self._upstream_dp_boundary = upstream_delta_pressure_boundary
        self._root_finding_strategy = root_finding_strategy

    def apply(
        self,
        *,
        input_cfg: PressureControlConfiguration,
        target_pressure: FloatConstraint,
        run_system: RunPressureControlCfg,
    ) -> tuple[Solution[PressureControlConfiguration], FluidStream]:
        baseline_cfg = input_cfg
        outlet_stream_at_baseline = run_system(baseline_cfg)

        # No choking needed if we are already at/below target.
        if outlet_stream_at_baseline.pressure_bara <= target_pressure.value + EPSILON:
            success = abs(outlet_stream_at_baseline.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
            return Solution(success=success, configuration=baseline_cfg), outlet_stream_at_baseline

        choke_solver = UpstreamChokeSolver(
            root_finding_strategy=self._root_finding_strategy,
            target_pressure=target_pressure.value,
            delta_pressure_boundary=self._upstream_dp_boundary,
        )

        def outlet_with_upstream_choke(ccfg: ChokeConfiguration) -> FluidStream:
            candidate_cfg = PressureControlConfiguration(
                speed=baseline_cfg.speed,
                recirculation_rate=baseline_cfg.recirculation_rate,
                upstream_delta_pressure=ccfg.delta_pressure,
                downstream_delta_pressure=baseline_cfg.downstream_delta_pressure,
            )
            return run_system(candidate_cfg)

        choke_solution = choke_solver.solve(outlet_with_upstream_choke)

        controlled_cfg = PressureControlConfiguration(
            speed=baseline_cfg.speed,
            recirculation_rate=baseline_cfg.recirculation_rate,
            upstream_delta_pressure=choke_solution.configuration.delta_pressure,
            downstream_delta_pressure=baseline_cfg.downstream_delta_pressure,
        )
        outlet_stream = run_system(controlled_cfg)

        success = abs(outlet_stream.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
        return Solution(success=success, configuration=controlled_cfg), outlet_stream


def _make_recirculation_eval_func(
    *,
    baseline_cfg: PressureControlConfiguration,
    run_system: RunPressureControlCfg,
) -> Callable[[RecirculationConfiguration], FluidStream]:
    """
    Build an evaluation function for `RecirculationSolver`.

    Keeps everything in `baseline_cfg` fixed (speed/chokes), varies only `recirculation_rate`.
    """

    def func(rcfg: RecirculationConfiguration) -> FluidStream:
        candidate_cfg = PressureControlConfiguration(
            speed=baseline_cfg.speed,
            recirculation_rate=rcfg.recirculation_rate,
            upstream_delta_pressure=baseline_cfg.upstream_delta_pressure,
            downstream_delta_pressure=baseline_cfg.downstream_delta_pressure,
        )
        return run_system(candidate_cfg)

    return func
