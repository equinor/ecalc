from collections.abc import Callable

import pytest

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.factories import create_pressure_control_policy
from libecalc.domain.process.process_solver.pressure_control.pressure_control_policies import (
    IndividualASVPressureControlPolicy,
    IndividualASVRatePressureControlPolicy,
)
from libecalc.domain.process.process_solver.pressure_control.types import (
    PressureControlConfiguration,
    PressureControlPolicyName,
    StageRunner,
)
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class LinearStageRunner(StageRunner):
    """
    Test stub: outlet_pressure = outlet_at_zero - k * recirculation_rate.
    Implements StageRunner protocol for use in unit tests.
    """

    def __init__(
        self,
        make_stream: Callable[[float], FluidStream],
        outlet_at_zero: float,
        k: float,
        boundary: Boundary = Boundary(min=0.0, max=1000.0),
    ):
        self._outlet_at_zero = outlet_at_zero
        self._k = k
        self._make_stream = make_stream

    def run(self, recirculation_rate: float) -> FluidStream:
        return self._make_stream(self._outlet_at_zero - self._k * recirculation_rate)

    def get_recirculation_boundary(self) -> Boundary:
        return Boundary(min=0.0, max=1000.0)


# --------------------------------------------
# COMMON_ASV pressure control policy tests
# --------------------------------------------


def test_common_asv_pressure_control_finds_recirculation_to_hit_target_pressure(make_stream):
    """Policy must find recirculation_rate that brings outlet pressure to target."""

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
        return make_stream(outlet_pressure)

    baseline_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    solution, outlet = common_asv_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        run_system=run_system,
    )

    assert solution.success is True
    assert solution.configuration.recirculation_rate == pytest.approx(expected_recirculation, abs=1e-2)
    assert outlet.pressure_bara == pytest.approx(target.value, abs=target.abs_tol)


# -----------------------------------------------
# DOWNSTREAM_CHOKE pressure control policy tests
# -----------------------------------------------
def test_downstream_choke_outlet_below_target_returns_baseline_without_choke(make_stream):
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
        return make_stream(outlet_pressure)

    baseline_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    solution, outlet = downstream_choke_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        run_system=run_system,
    )

    assert solution.success is False  # No choking applied, but that's expected since outlet is already below target.
    assert solution.configuration == baseline_cfg
    assert outlet.pressure_bara == 50.0


def test_downstream_choke_outlet_above_target_adds_downstream_delta_pressure(make_stream):
    """When outlet is above target, policy must add downstream_delta_pressure to bring it down."""

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
        return make_stream(outlet_pressure)

    baseline_cfg = PressureControlConfiguration(speed=100.0, recirculation_rate=0.0)

    solution, outlet = downstream_choke_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        run_system=run_system,
    )

    assert solution.success is True
    assert solution.configuration.downstream_delta_pressure == pytest.approx(expected_dp, abs=1e-12)
    assert outlet.pressure_bara == pytest.approx(target.value, abs=1e-12)


# -----------------------------------------------
# UPSTREAM_CHOKE pressure control policy tests
# -----------------------------------------------
def test_upstream_choke_outlet_above_target_finds_upstream_delta_pressure_root(make_stream):
    """When outlet is above target, policy must find upstream_delta_pressure that meets target."""

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
        return make_stream(outlet_pressure)

    baseline_cfg = PressureControlConfiguration(speed=100.0)

    solution, outlet = upstream_choke_policy.apply(
        input_cfg=baseline_cfg,
        target_pressure=target,
        run_system=run_system,
    )

    assert solution.success is True
    assert solution.configuration.upstream_delta_pressure == pytest.approx(expected_dp, abs=1e-7)
    assert outlet.pressure_bara == pytest.approx(target.value, abs=target.abs_tol)


def test_upstream_choke_outlet_below_target_returns_baseline_without_choke(make_stream):
    """Choking must not be applied when outlet pressure is already below target."""

    target = FloatConstraint(70.0, abs_tol=1e-10)

    policy = create_pressure_control_policy(
        PressureControlPolicyName.UPSTREAM_CHOKE,
        recirculation_rate_boundary=Boundary(min=0.0, max=1.0),  # unused
        upstream_delta_pressure_boundary=Boundary(min=0.0, max=50.0),
    )

    def run_system(cfg: PressureControlConfiguration) -> FluidStream:
        return make_stream(50.0)  # already below target

    solution, outlet = policy.apply(
        input_cfg=PressureControlConfiguration(speed=100.0),
        target_pressure=target,
        run_system=run_system,
    )

    assert solution.success is False
    assert outlet.pressure_bara == 50.0


# -----------------------------------------------
# INDIVIDUAL_ASV pressure control policy tests
# -----------------------------------------------
def test_individual_asv_pressure_control_distributes_pressure_equally_across_stages(make_stream):
    """
    Policy must distribute the target pressure equally across N stages (geometric mean)
    and find per-stage recirculation rates that meet per-stage target pressures.

    Model: outlet_pressure = inlet_pressure * ratio - k * recirculation_rate (linear)
    With equal pressure ratio per stage: ratio = (target / inlet) ^ (1/N)
    At zero recirculation, each stage hits its target exactly -> expected recirculation = 0.
    """

    n_stages = 2
    inlet_pressure = 30.0
    target_pressure = FloatConstraint(value=75.0, abs_tol=1e-6)
    pressure_ratio_per_stage = (target_pressure.value / inlet_pressure) ** (1.0 / n_stages)
    k = 0.001  # small sensitivity: recirculation slightly reduces outlet pressure

    # Stage 0: outlet = inlet * ratio - k * recirc
    # Stage 1: outlet = outlet_stage0 * ratio - k * recirc
    # At recirc=0: stage1_out = inlet * ratio^2 = target -> expected rates are ~0

    stage0_outlet_at_zero = inlet_pressure * pressure_ratio_per_stage
    stage1_outlet_at_zero = stage0_outlet_at_zero * pressure_ratio_per_stage  # at recirc=0 in stage 0

    def run_system(cfg: PressureControlConfiguration) -> FluidStream:
        rates = cfg.recirculation_rates_per_stage or (0.0, 0.0)
        p0_out = stage0_outlet_at_zero - k * rates[0]
        p1_out = p0_out * pressure_ratio_per_stage - k * rates[1]
        return make_stream(p1_out)

    policy = IndividualASVPressureControlPolicy(
        stage_runners=[
            LinearStageRunner(outlet_at_zero=stage0_outlet_at_zero, k=k, make_stream=make_stream),
            LinearStageRunner(outlet_at_zero=stage1_outlet_at_zero, k=k, make_stream=make_stream),
        ],
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-10),
        inlet_pressure=inlet_pressure,
    )

    solution, outlet = policy.apply(
        input_cfg=PressureControlConfiguration(speed=100.0),
        target_pressure=target_pressure,
        run_system=run_system,
    )

    assert solution.success is True
    # At recirc=0 model hits target exactly -> expected rates are ~0
    assert solution.configuration.recirculation_rates_per_stage[0] == pytest.approx(0.0, abs=1e-4)
    assert solution.configuration.recirculation_rates_per_stage[1] == pytest.approx(0.0, abs=1e-4)
    assert outlet.pressure_bara == pytest.approx(target_pressure.value, abs=target_pressure.abs_tol)


def test_individual_asv_pressure_control_finds_nonzero_recirculation_to_meet_stage_targets(make_stream):
    """
    Policy must find nonzero per-stage recirculation when outlet pressure exceeds per-stage targets.

    Model: outlet_pressure = outlet_at_zero - k * recirculation_rate (linear)
    Each stage overshoots its per-stage target at recirc=0 -> policy must find nonzero rates.

    Expected recirculation = (outlet_at_zero - per_stage_target) / k
    """

    n_stages = 2
    inlet_pressure = 30.0
    target_pressure = FloatConstraint(value=75.0, abs_tol=1e-6)
    k = 1.0  # 1:1 sensitivity: each unit of recirculation reduces outlet by 1 bara
    overshoot = 1.2  # each stage produces 20% above its per-stage target at recirc=0

    pressure_ratio_per_stage = (target_pressure.value / inlet_pressure) ** (1.0 / n_stages)

    stage0_target = inlet_pressure * pressure_ratio_per_stage
    stage0_outlet_at_zero = stage0_target * overshoot
    expected_rate_0 = (stage0_outlet_at_zero - stage0_target) / k

    # Policy uses actual outlet of stage 0 (≈ stage0_target after solving) as inlet for stage 1
    stage1_target = stage0_target * pressure_ratio_per_stage
    stage1_outlet_at_zero = stage1_target * overshoot
    expected_rate_1 = (stage1_outlet_at_zero - stage1_target) / k

    def run_system(cfg: PressureControlConfiguration) -> FluidStream:
        rates = cfg.recirculation_rates_per_stage or (0.0, 0.0)
        p0_out = stage0_outlet_at_zero - k * rates[0]
        p1_out = stage1_outlet_at_zero - k * rates[1]
        outlet = p0_out + p1_out - stage0_target  # simplified total outlet
        return make_stream(outlet)

    policy = IndividualASVPressureControlPolicy(
        stage_runners=[
            LinearStageRunner(outlet_at_zero=stage0_outlet_at_zero, k=k, make_stream=make_stream),
            LinearStageRunner(outlet_at_zero=stage1_outlet_at_zero, k=k, make_stream=make_stream),
        ],
        root_finding_strategy=ScipyRootFindingStrategy(tolerance=1e-10),
        inlet_pressure=inlet_pressure,
    )

    solution, outlet = policy.apply(
        input_cfg=PressureControlConfiguration(speed=100.0),
        target_pressure=target_pressure,
        run_system=run_system,
    )

    assert solution.success is True
    assert solution.configuration.recirculation_rates_per_stage[0] == pytest.approx(expected_rate_0, abs=1e-4)
    assert solution.configuration.recirculation_rates_per_stage[1] == pytest.approx(expected_rate_1, abs=1e-4)


def test_individual_asv_rate_pressure_control_policy_finds_fraction_to_meet_target_pressure(make_stream):
    """
    Testing INDIVIDUAL_ASV_PRESSURE policy:

    Policy must find the ASV rate fraction [0-1] that reduces discharge pressure to meet target.

    Model: pressure decreases linearly with fraction - fraction=0 gives max pressure, fraction=1 gives min pressure.
    Expected: policy finds the fraction where outlet pressure equals target.
    """

    max_pressure = 100.0
    min_pressure = 60.0
    target_pressure = FloatConstraint(value=80.0, abs_tol=0.1)

    # fraction=0 -> max_pressure, fraction=1 -> min_pressure
    expected_fraction = (max_pressure - target_pressure.value) / (max_pressure - min_pressure)  # = 0.5

    def run_system(cfg: PressureControlConfiguration) -> FluidStream:
        pressure = max_pressure - cfg.asv_rate_fraction * (max_pressure - min_pressure)
        return make_stream(pressure)

    policy = IndividualASVRatePressureControlPolicy(
        recirculation_fraction_boundary=Boundary(min=0.0, max=1.0),
        root_finding_strategy=ScipyRootFindingStrategy(),
    )

    input_cfg = PressureControlConfiguration(speed=100.0, asv_rate_fraction=0.0)
    solution, outlet = policy.apply(
        input_cfg=input_cfg,
        target_pressure=target_pressure,
        run_system=run_system,
    )

    assert solution.success is True
    assert solution.configuration.speed == 100.0
    assert solution.configuration.asv_rate_fraction == pytest.approx(expected_fraction, rel=1e-4)
    assert outlet.pressure_bara == pytest.approx(target_pressure.value, abs=target_pressure.abs_tol)
