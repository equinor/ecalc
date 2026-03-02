import pytest

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.policies import (
    CapacityPolicy,
    NoCapacityPolicy,
    NoPressureControlPolicy,
    PressureControlPolicy,
)
from libecalc.domain.process.process_solver.pressure_control.solver import PressureControlSolver
from libecalc.domain.process.process_solver.pressure_control.types import PressureControlConfiguration
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_system.process_error import OutsideCapacityError
from libecalc.domain.process.value_objects.fluid_stream import FluidStream
from tests.libecalc.domain.process.process_solver.pressure_control._test_utils import PressurePolicySpy, with_pressure


class PressurePolicySetRecircToOne(PressureControlPolicy):
    def apply(self, *, input_cfg: PressureControlConfiguration, target_pressure: FloatConstraint, evaluate_system):
        cfg2 = PressureControlConfiguration(
            speed=input_cfg.speed,
            recirculation_rate=1.0,
            upstream_delta_pressure=input_cfg.upstream_delta_pressure,
            downstream_delta_pressure=input_cfg.downstream_delta_pressure,
        )
        outlet = evaluate_system(cfg2)
        ok = abs(outlet.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
        return Solution(success=ok, configuration=cfg2), outlet


def test_pressure_control_solver_finds_speed_for_target_pressure(fluid_stream_mock):
    """
    Verify PressureControlSolver's *orchestration* of the outer speed loop.

    This test checks that the solver adjusts `configuration.speed` until the evaluated outlet pressure
    matches the target (within tolerance).

    We intentionally do NOT model a real compressor train here:
    the physical model is irrelevant for this unit test, and would make the test slower.
    Instead, we inject a deterministic `evaluate_system` where outlet pressure is a simple function of speed.
    """
    pressure_control_solver = PressureControlSolver(
        speed_boundary=Boundary(min=0.0, max=100.0),
        search_strategy=BinarySearchStrategy(tolerance=1e-9),
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-12),
        # Keep policies trivial so the test focuses on the speed solve.
        capacity_policy=NoCapacityPolicy(),
        pressure_control_policy=NoPressureControlPolicy(),
    )

    pressure_offset = 10.0  # Ensures positive pressures even at speed=0
    target = FloatConstraint(pressure_offset + 70.0, abs_tol=1e-6)

    inlet_stream = fluid_stream_mock

    def evaluate_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Fake "process model": monotonic pressure vs speed so SpeedSolver can find a root.
        return with_pressure(inlet_stream, pressure_bara=pressure_offset + cfg.speed)

    sol = pressure_control_solver.solve(target_pressure=target, evaluate_system=evaluate_system)

    assert sol.success is True
    assert sol.configuration.speed == pytest.approx(70.0, abs=target.abs_tol)


def test_pressure_control_solver_returns_max_speed_when_target_unreachable(fluid_stream_mock):
    """
    Verify PressureControlSolver returns a sensible best-effort result when the target is unreachable.

    What we test:
      - The solver tries to hit a target outlet pressure by varying speed.
      - If even max speed cannot produce a high enough outlet pressure, the solver must:
          * return success=False, and
          * return configuration.speed == speed_boundary.max (the best effort).

    Why the "fake" system:
      - This is an orchestration/algorithm test, not a compressor/NeqSim test.
      - We inject a deterministic evaluate_system with: outlet_pressure_bara = pressure_offset + speed.
    """
    speed_boundary = Boundary(min=0.0, max=100.0)

    pressure_control_solver = PressureControlSolver(
        speed_boundary=speed_boundary,
        search_strategy=BinarySearchStrategy(tolerance=1e-9),
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-12),
        # Keep policies trivial so we only test the speed outer loop behavior.
        capacity_policy=NoCapacityPolicy(),
        pressure_control_policy=NoPressureControlPolicy(),
    )

    pressure_offset = 10.0
    # With outlet = offset + speed and speed<=100, max achievable outlet is 110 => target 200 is unreachable.
    target = FloatConstraint(200.0, abs_tol=1e-6)

    inlet_stream = fluid_stream_mock

    def evaluate_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Deterministic "fake process": monotonic, but capped by speed boundary.
        return with_pressure(inlet_stream, pressure_bara=pressure_offset + cfg.speed)

    sol = pressure_control_solver.solve(target_pressure=target, evaluate_system=evaluate_system)

    assert sol.success is False
    assert sol.configuration.speed == speed_boundary.max


def test_pressure_control_solver_ignores_policy_success_until_target_is_met(
    fluid_stream_mock,
):
    """
    Ensure PressureControlSolver can still solve for speed even if the pressure-control policy reports success=False
    for intermediate speed evaluations.

    The pressure-control policy's success flag means "target met at this speed", not "solver should stop".
    This test uses a deterministic fake evaluate_system (outlet_pressure = offset + speed) and a downstream-choke-like
    no-op policy that never changes the configuration and only returns success=True when the target is met.
    """
    pressure_offset = 10.0
    target = FloatConstraint(pressure_offset + 70.0, abs_tol=1e-6)

    inlet_stream = fluid_stream_mock

    class DownstreamLikeNoOpPolicy(PressureControlPolicy):
        def apply(
            self,
            *,
            input_cfg: PressureControlConfiguration,
            target_pressure: FloatConstraint,
            evaluate_system,
        ) -> tuple[Solution[PressureControlConfiguration], FluidStream]:
            # Policy does not force success; it only reports whether the current speed evaluation meets target.
            outlet = evaluate_system(input_cfg)
            success = abs(outlet.pressure_bara - target_pressure.value) <= target_pressure.abs_tol
            return Solution(success=success, configuration=input_cfg), outlet

    solver = PressureControlSolver(
        speed_boundary=Boundary(min=0.0, max=200.0),
        search_strategy=BinarySearchStrategy(tolerance=1e-9),
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-12),
        capacity_policy=NoCapacityPolicy(),
        pressure_control_policy=DownstreamLikeNoOpPolicy(),
    )

    def evaluate_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Fake process: monotonic pressure vs speed.
        return with_pressure(inlet_stream, pressure_bara=pressure_offset + cfg.speed)

    sol = solver.solve(target_pressure=target, evaluate_system=evaluate_system)

    assert sol.success is True
    assert sol.configuration.speed == pytest.approx(70.0, abs=target.abs_tol)


def test_pressure_control_solver_capacity_failure_returns_best_effort(
    fluid_stream_mock,
):
    """
    Verify that a capacity failure at a given speed makes that speed "unusable" for PressureControlSolver.

    What we test:
      - CapacityPolicy may return success=False (meaning: no feasible operating point at this speed).
      - PressureControlSolver should treat that as OutsideCapacityError for the speed evaluation.
      - SpeedSolver then falls back to best-effort at max speed and returns success=False.

    This is an orchestration test: we avoid modelling any real process system. `evaluate_system` is deterministic and
    returns a mocked FluidStream with pressure derived from speed.
    """

    class AlwaysFailCapacityPolicy(CapacityPolicy):
        def apply(
            self,
            *,
            input_cfg: PressureControlConfiguration,
            evaluate_system,
        ) -> Solution[PressureControlConfiguration]:
            # Mark the speed evaluation as infeasible.
            return Solution(success=False, configuration=input_cfg)

    pressure_control_solver = PressureControlSolver(
        speed_boundary=Boundary(min=0.0, max=100.0),
        search_strategy=BinarySearchStrategy(tolerance=1e-9),
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-12),
        capacity_policy=AlwaysFailCapacityPolicy(),
        pressure_control_policy=NoPressureControlPolicy(),
    )

    target = FloatConstraint(70.0, abs_tol=1e-6)
    inlet_stream = fluid_stream_mock

    def evaluate_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Should never matter (capacity fails before pressure control), but keep it valid.
        return with_pressure(inlet_stream, pressure_bara=10.0 + cfg.speed)

    sol = pressure_control_solver.solve(target_pressure=target, evaluate_system=evaluate_system)

    assert sol.success is False
    assert sol.configuration.speed == 100.0


def test_pressure_control_solver_final_evaluation_failure_returns_best_effort(fluid_stream_mock):
    """
    Verify the solver's "best effort" fallback when the final evaluation fails.

    What we test:
      - SpeedSolver may still select a speed (typically max speed when the target is unreachable).
      - If evaluating the system at that selected speed raises a ProcessError (e.g. OutsideCapacityError),
        PressureControlSolver should return success=False and still return a configuration with that speed set.

    We keep this as a unit test by injecting a deterministic evaluate_system and using a mocked FluidStream
    (no NeqSim / no real process model).
    """
    pressure_control_solver = PressureControlSolver(
        speed_boundary=Boundary(min=0.0, max=100.0),
        search_strategy=BinarySearchStrategy(tolerance=1e-9),
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-12),
        capacity_policy=NoCapacityPolicy(),
        pressure_control_policy=NoPressureControlPolicy(),
    )

    # Unreachable with our fake model below => SpeedSolver will end up at max speed (best effort).
    target = FloatConstraint(200.0, abs_tol=1e-6)

    inlet_stream = fluid_stream_mock
    pressure_offset = 10.0

    def evaluate_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Force the final "best effort" evaluation at max speed to fail.
        if cfg.speed == 100.0:
            raise OutsideCapacityError()

        # Fake process: outlet pressure tracks speed.
        return with_pressure(inlet_stream, pressure_bara=pressure_offset + cfg.speed)

    sol = pressure_control_solver.solve(target_pressure=target, evaluate_system=evaluate_system)

    assert sol.success is False
    assert sol.configuration.speed == 100.0


def test_stage_a_never_calls_pressure_policy_more_than_once(fluid_stream_mock):
    """
    Contract: pressure-control policy must not be invoked inside the speed loop (Step A).

    With the current two-stage design (+ Step B short-circuit), total calls may be 0 or 1.
    But it should never be > 1. If it is > 1, pressure control leaked into Step A.
    """
    spy = PressurePolicySpy(PressurePolicySetRecircToOne())

    solver = PressureControlSolver(
        speed_boundary=Boundary(min=0.0, max=10.0),
        search_strategy=BinarySearchStrategy(tolerance=1e-6),
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-10),
        capacity_policy=NoCapacityPolicy(),
        pressure_control_policy=spy,
    )

    inlet_p = 100.0

    def evaluate_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Make pressure independent of recirculation so Step B short-circuit triggers (policy call count becomes 0).
        return with_pressure(stream=fluid_stream_mock, pressure_bara=inlet_p + cfg.speed)

    sol = solver.solve(target_pressure=FloatConstraint(inlet_p + 7.0, abs_tol=1e-6), evaluate_system=evaluate_system)

    assert sol.success is True
    assert spy.calls <= 1


def test_stage_b_calls_pressure_policy_once_when_baseline_pressure_saturates(fluid_stream_mock):
    """
    This test guarantees Step B cannot short-circuit:
    - baseline outlet pressure saturates at a max value (independent of further speed increase)
    - pressure control (recirculation=1) lifts the saturation limit so target becomes reachable

    Result: pressure_control_policy must be called exactly once in Step B.
    """
    spy = PressurePolicySpy(PressurePolicySetRecircToOne())

    solver = PressureControlSolver(
        speed_boundary=Boundary(min=0.0, max=10.0),
        search_strategy=BinarySearchStrategy(tolerance=1e-6),
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-10),
        capacity_policy=NoCapacityPolicy(),
        pressure_control_policy=spy,
    )

    inlet_p = 100.0
    baseline_ceiling = inlet_p + 8.0  # baseline can never exceed 108.0 regardless of speed

    def evaluate_system(cfg: PressureControlConfiguration) -> FluidStream:
        raw = inlet_p + cfg.speed

        if cfg.recirculation_rate == 1.0:
            # "Pressure control" lifts the ceiling so we can reach higher pressure
            p = min(raw, baseline_ceiling + 1.0)  # can reach up to 109.0
        else:
            # Baseline saturates
            p = min(raw, baseline_ceiling)

        return with_pressure(stream=fluid_stream_mock, pressure_bara=p)

    target = FloatConstraint(inlet_p + 8.5, abs_tol=1e-6)  # 108.5 unreachable for baseline, reachable with control

    sol = solver.solve(target_pressure=target, evaluate_system=evaluate_system)

    assert spy.calls == 1
    assert sol.configuration.recirculation_rate == 1.0
