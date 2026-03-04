from abc import ABC, abstractmethod

from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.types import (
    PressureControlConfiguration,
    RunPressureControlCfg,
    StageRunner,
)
from libecalc.domain.process.process_solver.pressure_control.utils import create_recirculation_eval_func
from libecalc.domain.process.process_solver.search_strategies import RootFindingStrategy, SearchStrategy
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import (
    ChokeConfiguration,
    DownstreamChokeSolver,
)
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationSolver
from libecalc.domain.process.process_solver.solvers.upstream_choke_solver import UpstreamChokeSolver
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


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

        recirculation_func = create_recirculation_eval_func(
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
    Implements pressure control for INDIVIDUAL_ASV_RATE.

    At fixed speed, finds a single ASV rate fraction [0-1] applied equally to all stages
    to meet target discharge pressure.

    Unlike IndividualASVPressureControlPolicy (INDIVIDUAL_ASV_PRESSURE, which solves
    per-stage recirculation rates independently), this policy adjusts all stages
    proportionally via a single scalar fraction.

    The caller must build run_system to:
    - read asv_rate_fraction from PressureControlConfiguration
    - apply it equally to all stages (e.g. via stage.rate_modifier.fraction_of_available_capacity_to_recirculate)
    - return the total outlet stream
    """

    def __init__(
        self,
        *,
        recirculation_fraction_boundary: Boundary,
        root_finding_strategy: RootFindingStrategy,
    ):
        self._recirculation_fraction_boundary = recirculation_fraction_boundary
        self._root_finding_strategy = root_finding_strategy

    def apply(
        self,
        *,
        input_cfg: PressureControlConfiguration,
        target_pressure: FloatConstraint,
        run_system: RunPressureControlCfg,
    ) -> tuple[Solution[PressureControlConfiguration], FluidStream]:
        # Find the ASV rate fraction [0-1] that meets target discharge pressure
        fraction = self._root_finding_strategy.find_root(
            boundary=self._recirculation_fraction_boundary,
            func=lambda f: run_system(
                PressureControlConfiguration(speed=input_cfg.speed, asv_rate_fraction=f)
            ).pressure_bara
            - target_pressure.value,
        )
        cfg = PressureControlConfiguration(
            speed=input_cfg.speed,
            asv_rate_fraction=fraction,
        )
        # Verify total outlet meets target pressure
        outlet = run_system(cfg)
        success = abs(outlet.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
        return Solution(success=success, configuration=cfg), outlet


class IndividualASVPressureControlPolicy(PressureControlPolicy):
    """
    Implements pressure control for INDIVIDUAL_ASV_PRESSURE.

    At fixed speed, distributes the target pressure equally across N stages
    using the geometric mean pressure ratio.

    Each stage is solved sequentially: given the inlet pressure at that stage, a root-finding
    strategy adjusts the recirculation rate until the stage outlet hits its per-stage target.
    The inlet to stage N+1 is the actual outlet of stage N (at the solved recirculation rate).

    The caller must build stage_runners such that stage_runners[i]:
    - closes over its RecirculationLoop and the current inlet stream for that stage
    - run(rate) returns the outlet FluidStream for the given recirculation rate [Sm3/day]
    - get_recirculation_boundary() returns the valid Boundary [Sm3/day] for the current
      speed and inlet stream (dynamic: evaluated at solve time, not at construction time)
    """

    def __init__(
        self,
        *,
        stage_runners: list[StageRunner],
        root_finding_strategy: RootFindingStrategy,
        inlet_pressure: float,
    ):
        self._stage_runners = stage_runners
        self._root_finding_strategy = root_finding_strategy
        self._inlet_pressure = inlet_pressure

    def apply(
        self,
        *,
        input_cfg: PressureControlConfiguration,
        target_pressure: FloatConstraint,
        run_system: RunPressureControlCfg,
    ) -> tuple[Solution[PressureControlConfiguration], FluidStream]:
        n = len(self._stage_runners)

        # Equal pressure ratio per stage: (target / inlet) ^ (1/N)
        pressure_ratio_per_stage = (target_pressure.value / self._inlet_pressure) ** (1.0 / n)

        rates = []
        current_pressure = self._inlet_pressure
        for stage_runner in self._stage_runners:
            per_stage_target = current_pressure * pressure_ratio_per_stage
            boundary = stage_runner.get_recirculation_boundary()  # dynamic: speed/inlet-dependent

            def outlet_pressure_residual(
                r: float,
                _runner: StageRunner = stage_runner,
                _target: float = per_stage_target,
            ) -> float:
                return _runner.run(r).pressure_bara - _target

            rate = self._root_finding_strategy.find_root(
                boundary=boundary,
                func=outlet_pressure_residual,
            )
            rates.append(rate)
            current_pressure = stage_runner.run(rate).pressure_bara  # outlet becomes inlet for next stage

        cfg = PressureControlConfiguration(
            speed=input_cfg.speed,
            recirculation_rates_per_stage=tuple(rates),
        )

        # Verify total outlet meets target pressure
        outlet = run_system(cfg)
        success = abs(outlet.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
        return Solution(success=success, configuration=cfg), outlet


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
