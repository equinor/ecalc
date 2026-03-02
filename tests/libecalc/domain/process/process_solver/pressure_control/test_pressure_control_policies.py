from typing import cast

import pytest

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.factories import create_pressure_control_policy
from libecalc.domain.process.process_solver.pressure_control.types import PressureControlConfiguration
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


def test_downstream_choke_outlet_below_target_returns_baseline_without_choke():
    """
    Unit test for DownstreamChokePressureControlPolicy when no choking is needed.

    This test does not model a real compressor or process system. Instead, `evaluate_system` is a stub that always
    returns an outlet stream with a fixed pressure.

    Scenario:
      - The outlet pressure with the baseline configuration is already below the target pressure.
      - The downstream choke policy should only add downstream pressure drop when outlet pressure is above target.
        Therefore, it must return the baseline configuration unchanged.

    What this test verifies:
      - The policy returns the baseline configuration (no added downstream_delta_pressure / no choke).
      - The returned outlet stream is the baseline outlet stream from `evaluate_system`.
    """

    target = FloatConstraint(70.0, abs_tol=1e-12)

    downstream_choke_policy = create_pressure_control_policy(
        "DOWNSTREAM_CHOKE",
        recirculation_rate_boundary=Boundary(min=0.0, max=1.0),  # unused by this policy
        upstream_delta_pressure_boundary=Boundary(min=0.0, max=1.0),  # unused by this policy
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-12),
        search_strategy=BinarySearchStrategy(tolerance=1e-9),
    )

    def evaluate_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Baseline outlet pressure below target -> the policy should not apply choking.
        outlet_pressure = 50.0
        return cast(FluidStream, type("S", (), {"pressure_bara": outlet_pressure})())

    baseline_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    solution, outlet = downstream_choke_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        evaluate_system=evaluate_system,
    )

    assert solution.success is False  # No choking applied, but that's expected since outlet is already below target.
    assert solution.configuration == baseline_cfg
    assert outlet.pressure_bara == 50.0


def test_downstream_choke_outlet_above_target_adds_downstream_delta_pressure():
    """
    Unit test for DownstreamChokePressureControlPolicy when choking is required.

    This test does not model a real compressor/process system. Instead, `evaluate_system` is a small deterministic
    stub that behaves like this:
        outlet_pressure = unchoked_outlet_pressure - downstream_delta_pressure

    Scenario:
      - With the baseline configuration (downstream_delta_pressure=0), the outlet pressure is above the target.
      - The downstream choke policy should therefore add a downstream pressure drop to bring the outlet pressure
        down to the target.

    Expected behavior:
      - The policy sets configuration.downstream_delta_pressure to (unchoked_outlet_pressure - target_pressure).
      - Evaluating the returned configuration yields outlet pressure approximately equal to the target (within abs_tol).
    """

    target = FloatConstraint(70.0, abs_tol=1e-12)
    unchoked_outlet_pressure = 100.0

    # In this simplified model, downstream choking reduces outlet pressure 1:1 with downstream_delta_pressure.
    expected_dp = unchoked_outlet_pressure - target.value

    downstream_choke_policy = create_pressure_control_policy(
        "DOWNSTREAM_CHOKE",
        recirculation_rate_boundary=Boundary(min=0.0, max=1.0),  # unused
        upstream_delta_pressure_boundary=Boundary(min=0.0, max=1.0),  # unused
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-12),
        search_strategy=BinarySearchStrategy(tolerance=1e-9),
    )

    def evaluate_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Model: downstream choke reduces outlet pressure by downstream_delta_pressure.
        outlet_pressure = unchoked_outlet_pressure - cfg.downstream_delta_pressure
        return cast(FluidStream, type("S", (), {"pressure_bara": outlet_pressure})())

    baseline_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    solution, outlet = downstream_choke_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        evaluate_system=evaluate_system,
    )

    assert solution.success is True
    assert solution.configuration.downstream_delta_pressure == pytest.approx(expected_dp, abs=1e-12)
    assert outlet.pressure_bara == pytest.approx(target.value, abs=1e-12)


def test_upstream_choke_outlet_above_target_finds_upstream_delta_pressure_root():
    """
    Unit test for UpstreamChokePressureControlPolicy when choking is required.

    This test does not model a real compressor or process system. Instead, `evaluate_system` is a deterministic stub
    with a simple linear relationship between upstream choking and outlet pressure:

        outlet_pressure = base_pressure - upstream_delta_pressure

    Scenario:
      - With the baseline configuration (upstream_delta_pressure=0), the outlet pressure is above the target.
      - The upstream choke policy should therefore choose an upstream_delta_pressure that makes the evaluated outlet
        pressure equal to the target (within abs_tol).

    Expected behavior:
      - upstream_delta_pressure is approximately (base_pressure - target_pressure).
      - Evaluating the returned configuration yields outlet pressure approximately equal to the target.
    """

    target = FloatConstraint(70.0, abs_tol=1e-10)
    base_pressure = 100.0

    # In this simplified model, choking upstream reduces outlet pressure 1:1 with upstream_delta_pressure.
    expected_dp = base_pressure - target.value  # 30

    upstream_choke_policy = create_pressure_control_policy(
        "UPSTREAM_CHOKE",
        recirculation_rate_boundary=Boundary(min=0.0, max=1.0),  # unused
        upstream_delta_pressure_boundary=Boundary(min=0.0, max=50.0),
    )

    def evaluate_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Deterministic stub: upstream choking reduces outlet pressure by upstream_delta_pressure.
        outlet_pressure = base_pressure - cfg.upstream_delta_pressure
        return cast(FluidStream, type("S", (), {"pressure_bara": outlet_pressure})())

    baseline_cfg = PressureControlConfiguration(speed=100.0)

    solution, outlet = upstream_choke_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        evaluate_system=evaluate_system,
    )

    assert solution.success is True
    assert solution.configuration.upstream_delta_pressure == pytest.approx(expected_dp, abs=1e-7)
    assert outlet.pressure_bara == pytest.approx(target.value, abs=target.abs_tol)


def test_common_asv_pressure_control_finds_recirculation_to_hit_target_pressure():
    """
    Unit test for CommonASVPressureControlPolicy (pressure control via recirculation at fixed speed).

    This is intentionally *not* a compressor/process-physics test. We use a small deterministic stub for `evaluate_system`
    where outlet pressure depends only on recirculation in a simple, predictable way:

        outlet_pressure = base_pressure - k * recirculation_rate

    Why this model:
      - Increasing recirculation always reduces outlet pressure (monotonic relationship).
      - The relationship is linear, so we can compute the expected recirculation analytically by rearranging the equation:

            target_pressure = base_pressure - k * recirculation_rate
        =>  recirculation_rate = (base_pressure - target_pressure) / k

    What this test verifies:
      - The policy returns success=True.
      - The returned configuration has recirculation_rate close to the analytically expected value.
      - Evaluating that configuration yields an outlet pressure within abs_tol of the target.
    """

    target = FloatConstraint(70.0, abs_tol=1e-6)
    base_pressure = 100.0
    k = 0.1
    expected_recirculation = (base_pressure - target.value) / k  # 300

    common_asv_policy = create_pressure_control_policy(
        "COMMON_ASV",
        recirculation_rate_boundary=Boundary(min=0.0, max=1000.0),
        upstream_delta_pressure_boundary=Boundary(min=0.0, max=0.0),  # unused
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-10),
        search_strategy=BinarySearchStrategy(tolerance=1e-6),
    )

    def evaluate_system(cfg: PressureControlConfiguration) -> FluidStream:
        # Deterministic stub: recirculation reduces outlet pressure linearly.
        outlet_pressure = base_pressure - k * cfg.recirculation_rate
        return cast(FluidStream, type("S", (), {"pressure_bara": outlet_pressure})())

    baseline_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    solution, outlet = common_asv_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        evaluate_system=evaluate_system,
    )

    assert solution.success is True
    assert solution.configuration.recirculation_rate == pytest.approx(expected_recirculation, abs=1e-2)
    assert outlet.pressure_bara == pytest.approx(target.value, abs=target.abs_tol)
