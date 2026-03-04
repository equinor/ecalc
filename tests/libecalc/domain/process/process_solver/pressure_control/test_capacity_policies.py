from collections.abc import Callable
from typing import cast

import pytest

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.pressure_control.capacity_policies import IndividualASVMinFlowPolicy
from libecalc.domain.process.process_solver.pressure_control.factories import create_capacity_policy
from libecalc.domain.process.process_solver.pressure_control.types import (
    CapacityPolicyName,
    PressureControlConfiguration,
    StageRunner,
)
from libecalc.domain.process.process_system.process_error import RateTooHighError, RateTooLowError
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class MinFlowStageRunner(StageRunner):
    """
    Test stub implementing StageRunner protocol for IndividualASVMinFlowPolicy tests.

    run() records calls for later assertion.
    get_minimum_recirculation_rate() returns a rate from a callable,
    allowing dynamic dependency on prior stages.
    """

    def __init__(
        self,
        make_stream: Callable[[float], FluidStream],
        min_rate_fn: Callable[[], float],
        observed_rates: list,
        label: str,
    ):
        self._make_stream = make_stream
        self._min_rate_fn = min_rate_fn
        self._observed_rates = observed_rates
        self._label = label

    def run(self, recirculation_rate: float) -> FluidStream:
        self._observed_rates.append((self._label, recirculation_rate))
        return self._make_stream(recirculation_rate)

    def get_recirculation_boundary(self) -> Boundary:
        return Boundary(min=0.0, max=1000.0)

    def get_minimum_recirculation_rate(self) -> float:
        return self._min_rate_fn()


# --------------------------------------------------
# COMMON_ASV_MIN_FLOW capacity control policy tests
# --------------------------------------------------
def test_common_asv_min_capacity_policy_finds_minimum_recirculation():
    """Policy must find the minimum recirculation rate that resolves RateTooLowError."""

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


def test_common_asv_min_flow_rate_too_high_propagates():
    """RateTooHighError must propagate — policy only handles RateTooLowError."""

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


# -----------------------------------------------------
# INDIVIDUAL_ASV_MIN_FLOW capacity control policy tests
# -----------------------------------------------------
def test_individual_asv_min_flow_policy_sets_minimum_rate_per_stage(make_stream):
    """
    Policy must apply the minimum recirculation rate independently per stage.

    Model: min_rate_stage_2 depends on stage 1 having run - proving sequential dependency.
    Expected: rates are set sequentially with correct minimum rates per stage.
    """

    stage1_min_rate = 50.0
    stage2_min_rate = 30.0

    observed_rates = []
    stage1_has_run = [False]  # mutable container

    def run_system(cfg: PressureControlConfiguration) -> FluidStream:
        return cast(FluidStream, object())

    def min_rate_stage1() -> float:
        stage1_has_run[0] = True  # side effect: mark stage 1 as having computed its min rate
        return stage1_min_rate

    def min_rate_stage2() -> float:
        # Depends on stage 1 having run - proves sequential execution
        assert stage1_has_run[0], "stage 1 must have run before stage 2"
        return stage2_min_rate

    policy = IndividualASVMinFlowPolicy(
        stage_runners=[
            MinFlowStageRunner(
                make_stream=make_stream,
                min_rate_fn=min_rate_stage1,
                observed_rates=observed_rates,
                label="stage1",
            ),
            MinFlowStageRunner(
                make_stream=make_stream,
                min_rate_fn=min_rate_stage2,
                observed_rates=observed_rates,
                label="stage2",
            ),
        ]
    )

    result = policy.apply(
        input_cfg=PressureControlConfiguration(speed=100.0),
        run_system=run_system,
    )

    assert result.configuration.speed == 100.0
    assert result.configuration.recirculation_rates_per_stage == (stage1_min_rate, stage2_min_rate)
    assert observed_rates == [("stage1", stage1_min_rate), ("stage2", stage2_min_rate)]
