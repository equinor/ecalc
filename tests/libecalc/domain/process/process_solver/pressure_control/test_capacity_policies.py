from typing import cast

import pytest

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.pressure_control.factories import create_capacity_policy
from libecalc.domain.process.process_solver.pressure_control.types import (
    CapacityPolicyName,
    PressureControlConfiguration,
)
from libecalc.domain.process.process_system.process_error import RateTooHighError, RateTooLowError
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


def test_common_asv_min_capacity_policy_finds_minimum_recirculation():
    """
    Policy must find the minimum recirculation rate that resolves RateTooLowError.

    Model: RateTooLowError iff (inlet_rate + recirculation_rate) < minimum_total_rate
    Expected recirculation_rate = minimum_total_rate - inlet_rate
    """

    inlet_rate = 200.0
    minimum_total_rate_through_compressor = 250.0
    expected_min_recirculation = minimum_total_rate_through_compressor - inlet_rate  # = 200.0

    capacity_policy = create_capacity_policy(
        CapacityPolicyName.COMMON_ASV_MIN_FLOW,
        recirculation_rate_boundary=Boundary(min=0.0, max=1000.0),
    )

    def run_system(cfg: PressureControlConfiguration):
        # "Feasible" once total internal flow through the compressor is high enough.
        total_rate = inlet_rate + cfg.recirculation_rate
        if total_rate < minimum_total_rate_through_compressor:
            raise RateTooLowError()
        return cast(FluidStream, object())

    input_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)
    capacity_solution = capacity_policy.apply(input_cfg=input_cfg, run_system=run_system)

    assert capacity_solution.success is True
    assert capacity_solution.configuration.recirculation_rate == pytest.approx(expected_min_recirculation, rel=0.01)

    # Verify that slightly lower recirculation is infeasible in our model.
    with pytest.raises(RateTooLowError):
        run_system(
            PressureControlConfiguration(
                speed=100.0,
                recirculation_rate=expected_min_recirculation * 0.99,
            )
        )


def test_common_asv_min_flow_ok_returns_input_unchanged():
    """Already feasible at baseline — policy must return input configuration unchanged."""

    capacity_policy = create_capacity_policy(
        CapacityPolicyName.COMMON_ASV_MIN_FLOW,
        recirculation_rate_boundary=Boundary(min=0.0, max=1000.0),
    )

    def run_system(cfg: PressureControlConfiguration):
        # Always feasible for this test: no capacity errors are raised.
        return cast(FluidStream, object())

    input_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    capacity_solution = capacity_policy.apply(input_cfg=input_cfg, run_system=run_system)

    assert capacity_solution.success is True
    assert capacity_solution.configuration == input_cfg


def test_common_asv_min_flow_rate_too_high_failure():
    """
    RateTooHighError must propagate unchanged — policy only handles RateTooLowError
    and must not attempt to repair a maximum-flow violation.
    """

    capacity_policy = create_capacity_policy(
        CapacityPolicyName.COMMON_ASV_MIN_FLOW,
        recirculation_rate_boundary=Boundary(min=0.0, max=1000.0),
    )

    def run_system(cfg: PressureControlConfiguration):
        # Always infeasible due to too-high rate (right of capacity envelope).
        raise RateTooHighError()

    input_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    with pytest.raises(RateTooHighError):
        capacity_policy.apply(input_cfg=input_cfg, run_system=run_system)
