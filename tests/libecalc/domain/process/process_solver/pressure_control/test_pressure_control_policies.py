from typing import cast

import pytest

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.factories import create_pressure_control_policy
from libecalc.domain.process.process_solver.pressure_control.types import (
    PressureControlConfiguration,
    PressureControlPolicyName,
)
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


def test_downstream_choke_outlet_below_target_returns_baseline_without_choke():
    """Choking must not be applied when outlet pressure is already below target."""

    target = FloatConstraint(70.0, abs_tol=1e-12)

    downstream_choke_policy = create_pressure_control_policy(
        PressureControlPolicyName.DOWNSTREAM_CHOKE,
        recirculation_rate_boundary=Boundary(min=0.0, max=1.0),  # unused by this policy
        upstream_delta_pressure_boundary=Boundary(min=0.0, max=1.0),  # unused by this policy
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-12),
        search_strategy=BinarySearchStrategy(tolerance=1e-9),
    )

    def run_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Baseline outlet pressure below target -> the policy should not apply choking.
        outlet_pressure = 50.0
        return cast(FluidStream, type("S", (), {"pressure_bara": outlet_pressure})())

    baseline_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    solution, outlet = downstream_choke_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        run_system=run_system,
    )

    assert solution.success is False  # No choking applied, but that's expected since outlet is already below target.
    assert solution.configuration == baseline_cfg
    assert outlet.pressure_bara == 50.0


def test_downstream_choke_outlet_above_target_adds_downstream_delta_pressure():
    """
    When outlet is above target, the policy must add downstream_delta_pressure to bring it down.

    Model: outlet_pressure = unchoked_outlet_pressure - downstream_delta_pressure (linear, 1:1)
    Expected downstream_delta_pressure = unchoked_outlet_pressure - target_pressure
    """

    target = FloatConstraint(70.0, abs_tol=1e-12)
    unchoked_outlet_pressure = 100.0

    # In this simplified model, downstream choking reduces outlet pressure 1:1 with downstream_delta_pressure.
    expected_dp = unchoked_outlet_pressure - target.value

    downstream_choke_policy = create_pressure_control_policy(
        PressureControlPolicyName.DOWNSTREAM_CHOKE,
        recirculation_rate_boundary=Boundary(min=0.0, max=1.0),  # unused
        upstream_delta_pressure_boundary=Boundary(min=0.0, max=1.0),  # unused
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-12),
        search_strategy=BinarySearchStrategy(tolerance=1e-9),
    )

    def run_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Model: downstream choke reduces outlet pressure by downstream_delta_pressure.
        outlet_pressure = unchoked_outlet_pressure - cfg.downstream_delta_pressure
        return cast(FluidStream, type("S", (), {"pressure_bara": outlet_pressure})())

    baseline_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    solution, outlet = downstream_choke_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        run_system=run_system,
    )

    assert solution.success is True
    assert solution.configuration.downstream_delta_pressure == pytest.approx(expected_dp, abs=1e-12)
    assert outlet.pressure_bara == pytest.approx(target.value, abs=1e-12)


def test_upstream_choke_outlet_above_target_finds_upstream_delta_pressure_root():
    """
    When outlet is above target, the policy must find upstream_delta_pressure that meets target.

    Model: outlet_pressure = base_pressure - upstream_delta_pressure (linear, 1:1)
    Expected upstream_delta_pressure = base_pressure - target_pressure
    """

    target = FloatConstraint(70.0, abs_tol=1e-10)
    base_pressure = 100.0

    # In this simplified model, choking upstream reduces outlet pressure 1:1 with upstream_delta_pressure.
    expected_dp = base_pressure - target.value  # 30

    upstream_choke_policy = create_pressure_control_policy(
        PressureControlPolicyName.UPSTREAM_CHOKE,
        recirculation_rate_boundary=Boundary(min=0.0, max=1.0),  # unused
        upstream_delta_pressure_boundary=Boundary(min=0.0, max=50.0),
    )

    def run_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Deterministic stub: upstream choking reduces outlet pressure by upstream_delta_pressure.
        outlet_pressure = base_pressure - cfg.upstream_delta_pressure
        return cast(FluidStream, type("S", (), {"pressure_bara": outlet_pressure})())

    baseline_cfg = PressureControlConfiguration(speed=100.0)

    solution, outlet = upstream_choke_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        run_system=run_system,
    )

    assert solution.success is True
    assert solution.configuration.upstream_delta_pressure == pytest.approx(expected_dp, abs=1e-7)
    assert outlet.pressure_bara == pytest.approx(target.value, abs=target.abs_tol)


def test_common_asv_pressure_control_finds_recirculation_to_hit_target_pressure():
    """
    Policy must find recirculation_rate that brings outlet pressure to target.

    Model: outlet_pressure = base_pressure - k * recirculation_rate (linear)
    Expected recirculation_rate = (base_pressure - target_pressure) / k
    """

    target = FloatConstraint(70.0, abs_tol=1e-6)
    base_pressure = 100.0
    k = 0.1
    expected_recirculation = (base_pressure - target.value) / k  # 300

    common_asv_policy = create_pressure_control_policy(
        PressureControlPolicyName.COMMON_ASV,
        recirculation_rate_boundary=Boundary(min=0.0, max=1000.0),
        upstream_delta_pressure_boundary=Boundary(min=0.0, max=0.0),  # unused
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-10),
        search_strategy=BinarySearchStrategy(tolerance=1e-6),
    )

    def run_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Deterministic stub: recirculation reduces outlet pressure linearly.
        outlet_pressure = base_pressure - k * cfg.recirculation_rate
        return cast(FluidStream, type("S", (), {"pressure_bara": outlet_pressure})())

    baseline_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    solution, outlet = common_asv_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        run_system=run_system,
    )

    assert solution.success is True
    assert solution.configuration.recirculation_rate == pytest.approx(expected_recirculation, abs=1e-2)
    assert outlet.pressure_bara == pytest.approx(target.value, abs=target.abs_tol)
