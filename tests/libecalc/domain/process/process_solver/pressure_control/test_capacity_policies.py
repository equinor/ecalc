from typing import cast

import pytest

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.pressure_control.factories import create_capacity_policy
from libecalc.domain.process.process_solver.pressure_control.types import PressureControlConfiguration
from libecalc.domain.process.process_system.process_error import RateTooHighError, RateTooLowError
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


def test_common_asv_min_capacity_policy_finds_minimum_recirculation():
    """
    Unit test for CommonASVMinCapacityPolicy.

    We model a minimum-flow capacity limit using a simple threshold:
        evaluation succeeds iff (inlet_rate + recirculation_rate) >= minimum_total_rate_through_compressor.
        If the threshold is not met, evaluate_system raises RateTooLowError.

    The policy is expected to:
      1) detect RateTooLowError at the baseline configuration (recirculation_rate=0), and
      2) increase recirculation_rate to the *minimum* value that makes evaluation succeed.

    This test does not build a real compressor chart; it only verifies the policy logic and its integration
    with RecirculationSolver in capacity-only mode (target_pressure=None).
    """

    inlet_rate = 200.0
    minimum_total_rate_through_compressor = 250.0
    expected_min_recirculation = minimum_total_rate_through_compressor - inlet_rate  # = 200.0

    capacity_policy = create_capacity_policy(
        "COMMON_ASV_MIN_FLOW",
        recirculation_rate_boundary=Boundary(min=0.0, max=1000.0),
    )

    def evaluate_system(cfg: PressureControlConfiguration):
        # "Feasible" once total internal flow through the compressor is high enough.
        total_rate = inlet_rate + cfg.recirculation_rate
        if total_rate < minimum_total_rate_through_compressor:
            raise RateTooLowError()
        return cast(FluidStream, object())

    input_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)
    capacity_solution = capacity_policy.apply(input_cfg=input_cfg, evaluate_system=evaluate_system)

    assert capacity_solution.success is True
    assert capacity_solution.configuration.recirculation_rate == pytest.approx(expected_min_recirculation, rel=0.01)

    # Verify that slightly lower recirculation is infeasible in our model.
    with pytest.raises(RateTooLowError):
        evaluate_system(
            PressureControlConfiguration(
                speed=100.0,
                recirculation_rate=expected_min_recirculation * 0.99,
            )
        )


def test_common_asv_min_flow_ok_returns_input_unchanged():
    """
    Unit test for CommonASVMinCapacityPolicy when no capacity violation occurs.

    This test does not model a real compressor/chart. Instead, we use a trivial `evaluate_system`
    stub that always succeeds (i.e. it never raises RateTooLowError/RateTooHighError). The goal is
    to verify the policy contract, not compressor physics.

    Scenario:
      - The baseline configuration is already feasible (evaluate_system does not raise RateTooLowError).
      - The capacity policy should therefore return the input configuration unchanged.

    What this test verifies:
      - apply(...) returns success=True
      - the returned configuration is exactly the input configuration (speed/recirculation/chokes unchanged)
    """

    capacity_policy = create_capacity_policy(
        "COMMON_ASV_MIN_FLOW",
        recirculation_rate_boundary=Boundary(min=0.0, max=1000.0),
    )

    def evaluate_system(cfg: PressureControlConfiguration):
        # Always feasible for this test: no capacity errors are raised.
        return cast(FluidStream, object())

    input_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    capacity_solution = capacity_policy.apply(input_cfg=input_cfg, evaluate_system=evaluate_system)

    assert capacity_solution.success is True
    assert capacity_solution.configuration == input_cfg


def test_common_asv_min_flow_rate_too_high_failure():
    """
    Unit test for CommonASVMinCapacityPolicy when the operating point is outside capacity due to too high rate.

    Key point:
      - This capacity policy is only designed to handle RateTooLowError by increasing recirculation
        (i.e. fixing a minimum-flow violation).
      - If the system evaluation raises RateTooHighError (a maximum-flow violation), increasing recirculation
        cannot help, and the policy should not try to "repair" the situation.

    Test setup:
      - We do not model a real compressor or chart here. This is a pure policy unit test.
      - `evaluate_system` is mocked to always raise RateTooHighError, representing "rate too high" at this speed.

    Expected behavior:
      - The policy propagates RateTooHighError (i.e. it fails fast rather than returning a modified configuration).
    """

    capacity_policy = create_capacity_policy(
        "COMMON_ASV_MIN_FLOW",
        recirculation_rate_boundary=Boundary(min=0.0, max=1000.0),
    )

    def evaluate_system(cfg: PressureControlConfiguration):
        # Always infeasible due to too-high rate (right of capacity envelope).
        raise RateTooHighError()

    input_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    with pytest.raises(RateTooHighError):
        capacity_policy.apply(input_cfg=input_cfg, evaluate_system=evaluate_system)


def test_common_asv_min_flow_no_feasible_point_returns_unsuccessful_solution():
    """
    Unit test for CommonASVMinCapacityPolicy when no feasible point exists within the allowed recirculation range.

    This test does not model a real compressor/chart. Instead, we use a simple feasibility rule:
        - evaluate_system raises RateTooLowError unless recirculation_rate >= min_feasible_recirculation_rate.

    We choose a recirculation boundary that is too small to ever satisfy the feasibility rule. The capacity policy
    should then return a "best effort" configuration (at the boundary limit), but mark the result as unsuccessful
    (success=False) because it could not get within capacity.
    """

    # Recirculation boundary is intentionally too small to reach the feasible threshold.
    recirculation_rate_boundary = Boundary(min=0.0, max=100.0)
    min_feasible_recirculation_rate = 200.0  # unreachable with max=100.0

    capacity_policy = create_capacity_policy(
        "COMMON_ASV_MIN_FLOW",
        recirculation_rate_boundary=recirculation_rate_boundary,
    )

    def evaluate_system(cfg: PressureControlConfiguration):
        if cfg.recirculation_rate < min_feasible_recirculation_rate:
            raise RateTooLowError()
        return cast(FluidStream, object())

    input_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    capacity_solution = capacity_policy.apply(input_cfg=input_cfg, evaluate_system=evaluate_system)
    assert capacity_solution.success is False
    # Best effort: the policy should push recirculation to the maximum allowed boundary.
    assert capacity_solution.configuration.recirculation_rate == pytest.approx(recirculation_rate_boundary.max)
