import pytest

from libecalc.common.units import Unit
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.feasibility_solver import FeasibilitySolver
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.shaft import VariableSpeedShaft
from libecalc.testing.chart_data_factory import ChartDataFactory

# ── Rate-axis constants ──────────────────────────────────────────────────────
_LOW_HEAD_TARGET = 55.0  # ~70 kJ/kg;  path lies below all surge heads
_HIGH_HEAD_TARGET = 100.0  # ~170 kJ/kg; path lies above all stonewall heads

# Probe-verified capacity limits: excess transitions 0 → > 0 at
#   LowHead  (55 bara): ~3 961 319 sm³/day  |  HighHead (100 bara): ~4 702 856 sm³/day
_LOW_HEAD_INSIDE = 3_507_473  # mid-range, well inside chart
_LOW_HEAD_OUTSIDE = 4_500_000  # above capacity limit (~3 961 319 sm³/day)
_HIGH_HEAD_INSIDE = 3_783_164  # mid-range, well inside chart
_HIGH_HEAD_OUTSIDE = 5_200_000  # above capacity limit (~4 702 856 sm³/day)

# ── Head-axis constants ──────────────────────────────────────────────────────
# Low rate: ~3 500 m³/h (2 710 050 sm³/day), feasible 49–116 bara
#   Vertical line intersects: min-speed curve (7 689 rpm) at 78.5 kJ/kg, surge line at 121.1 kJ/kg
#   Left-of-min-speed region: 49–~55 bara (recirculate at 7 689 rpm toward stonewall)
#   Left-of-surge region: above ~106 kJ/kg (speeds ≥ 9 886 rpm have surge > 3 500 m³/h)
_LOW_RATE_HEAD_PATH_RATE = 2_710_050  # sm³/day ≈ 3 500 m³/h actual
_LOW_RATE_HEAD_PATH_BELOW_MIN = 35.0  # below min achievable (~49 bara)
_LOW_RATE_HEAD_PATH_LEFT_MIN_SPD = 52.0  # below 7 689 rpm head at 3 500 m³/h; achievable via recirculation
_LOW_RATE_HEAD_PATH_INSIDE = 80.0  # inside chart (natural operation)
_LOW_RATE_HEAD_PATH_LEFT_SURGE = 108.0  # above 8 787 rpm region; 9 886+ rpm recirculate (left of surge)
_LOW_RATE_HEAD_PATH_ABOVE_MAX = 122.0  # above max achievable (~116 bara)

# High rate: ~6 000 m³/h (4 645 800 sm³/day), feasible 67–101 bara
#   Only speeds ≥ 10 435 rpm can cover 6 000 m³/h (lower speeds stonewall-limited)
#   Vertical line intersects: stonewall at 101.2 kJ/kg, max-speed curve at 162.3 kJ/kg
#   Right-of-max-speed region: 101–116 bara (above natural 11 533 rpm head at 6 000 m³/h but below
#     global max ~116 bara; achievable at lower net rate → partial excess)
#   No left-of-surge region: 6 000 m³/h is right of all surge points (max surge 4 328 m³/h)
#   No distinct left-of-min-speed region: at 6 000 m³/h the lowest feasible speed (10 435 rpm) is
#     already near its stonewall, so the recirculation band merges with the below-achievable boundary
_HIGH_RATE_HEAD_PATH_RATE = 4_645_800  # sm³/day ≈ 6 000 m³/h actual
_HIGH_RATE_HEAD_PATH_BELOW_MIN = 50.0  # below min achievable (~67 bara); rate-conditional → partial excess
_HIGH_RATE_HEAD_PATH_INSIDE = 85.0  # inside chart (natural operation)
_HIGH_RATE_HEAD_PATH_RIGHT_MAX_SPD = 105.0  # above 11 533 rpm head at 6 000 m³/h (~101 bara); partial excess
_HIGH_RATE_HEAD_PATH_ABOVE_MAX = 125.0  # above global max achievable (~116 bara) → full excess

# ── Two-stage series constants ───────────────────────────────────────────────
# Two identical Unisim stages on a shared shaft with inter-stage cooling to 303.15 K.
# Two-stage window (30 bara inlet): min achievable ~100 bara, max achievable ~450 bara.
# At 250 bara: capacity ~4 750 000 sm³/day.
_TWO_STAGE_TARGET = 250.0  # achievable by both stages in series
_TWO_STAGE_ABOVE_MAX_TARGET = 500.0  # above two-stage maximum achievable (~450 bara)
_TWO_STAGE_INSIDE_RATE = 2_710_050  # well inside capacity at 250 bara
_TWO_STAGE_HIGH_RATE = 6_000_000  # exceeds two-stage capacity at 250 bara

_HEAD_CONV = Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)

# Unisim methane compressor chart: (speed_rpm, [(rate_m3h, head_m, efficiency), ...])
_UNISIM_CURVES = [
    (
        7689,
        [(2900.07, 8412.92, 0.723), (3503.81, 7996.25, 0.747), (4002.56, 7363.82, 0.745), (4595.01, 6127.17, 0.702)],
    ),
    (
        8787,
        [
            (3305.57, 10950.96, 0.724),
            (4000.15, 10393.39, 0.745),
            (4499.23, 9707.49, 0.746),
            (4996.87, 8593.86, 0.722),
            (5241.99, 7974.60, 0.701),
        ],
    ),
    (
        9886,
        [
            (3708.87, 13845.38, 0.723),
            (4502.25, 13182.69, 0.747),
            (4993.60, 12425.37, 0.748),
            (5507.81, 11276.40, 0.731),
            (5924.33, 10054.35, 0.704),
        ],
    ),
    (
        10435,
        [
            (3928.04, 15435.48, 0.723),
            (4507.47, 14982.74, 0.744),
            (5002.12, 14350.22, 0.745),
            (5498.99, 13361.32, 0.741),
            (6248.59, 11183.03, 0.701),
        ],
    ),
    (
        10767,
        [
            (4052.91, 16447.0, 0.724),
            (4500.66, 16081.0, 0.738),
            (4999.41, 15546.0, 0.748),
            (5492.82, 14640.0, 0.748),
            (6000.63, 13454.0, 0.730),
            (6439.49, 11973.0, 0.701),
        ],
    ),
    (
        10984,
        [
            (4138.70, 17078.90, 0.723),
            (5002.48, 16274.92, 0.746),
            (5494.37, 15428.51, 0.747),
            (6008.70, 14261.72, 0.735),
            (6560.15, 12382.75, 0.702),
        ],
    ),
    (
        11533,
        [
            (4327.92, 18882.31, 0.725),
            (4998.52, 18235.19, 0.744),
            (5505.89, 17531.63, 0.745),
            (6027.62, 16489.72, 0.747),
            (6506.91, 15037.15, 0.727),
            (6908.28, 13618.79, 0.702),
        ],
    ),
]


@pytest.fixture
def compressor(fluid_service):
    """Variable-speed compressor using the Unisim methane chart for all FeasibilitySolver tests.

    Seven speed curves (7 689–11 533 rpm) with 4–6 points each.  Head values are
    converted from meter liquid column to J/kg.  The reference inlet (500 000 sm³/day,
    30 bara, medium gas) gives an actual volumetric rate well below the minimum-speed
    surge, so anti-surge recirculation is always active in normal operation.
    """
    curves = [
        ChartCurve(
            rate_actual_m3_hour=[p[0] for p in pts],
            polytropic_head_joule_per_kg=[_HEAD_CONV(p[1]) for p in pts],
            efficiency_fraction=[p[2] for p in pts],
            speed_rpm=float(speed),
        )
        for speed, pts in _UNISIM_CURVES
    ]
    return Compressor(
        process_unit_id=ProcessUnitId(ecalc_id_generator()),
        compressor_chart=ChartDataFactory.from_curves(curves),
        fluid_service=fluid_service,
    )


@pytest.fixture
def feasibility_solver_setup(
    process_runner_factory,
    process_pipeline_factory,
    with_individual_asv,
    individual_asv_anti_surge_strategy_factory,
    individual_asv_rate_control_strategy_factory,
    outlet_pressure_solver_factory,
):
    """Factory fixture: build a fully-wired FeasibilitySolver for a given compressor.

    Uses individual ASV rate control as the pressure control strategy, so both
    failure modes are exercisable:
      - too high: max-speed outlet pressure < target (head deficit)
      - too low:  min achievable outlet pressure (max recirculation) > target
    """

    def _create(compressor: Compressor) -> FeasibilitySolver:
        shaft = VariableSpeedShaft()
        shaft.connect(compressor)

        process_units, loops = with_individual_asv([compressor])
        loop_ids = [loop.get_id() for loop in loops]
        runner = process_runner_factory(
            units=process_units,
            configuration_handlers=[shaft, *loops],
        )
        process_pipeline = process_pipeline_factory(units=process_units)
        anti_surge = individual_asv_anti_surge_strategy_factory(
            runner=runner,
            recirculation_loop_ids=loop_ids,
            compressors=[compressor],
        )
        pressure_control = individual_asv_rate_control_strategy_factory(
            runner=runner,
            recirculation_loop_ids=loop_ids,
            compressors=[compressor],
        )
        outlet_pressure_solver = outlet_pressure_solver_factory(
            shaft=shaft,
            runner=runner,
            anti_surge_strategy=anti_surge,
            pressure_control_strategy=pressure_control,
            process_pipeline_id=process_pipeline.get_id(),
        )

        return FeasibilitySolver(outlet_pressure_solver=outlet_pressure_solver)

    return _create


class TestRateAxisLowHead:
    """Constant-pressure path at 55 bara (~70 kJ/kg) — sweep rate left to right.

    At h=70 the path lies entirely below the surge line (lowest surge head 82.5 kJ/kg
    at 7 689 rpm), so the chart envelope is bounded by the min-speed curve on the left
    and the stonewall on the right.  Below the left boundary the compressor recirculates;
    above the right boundary it still handles the flow via higher speeds, up to the
    solver capacity limit (~3 961 319 sm³/day).
    """

    def test_left_of_chart(self, feasibility_solver_setup, compressor, stream_factory):
        """Rate below chart envelope (recirculation zone) → excess = 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=500_000.0, pressure_bara=30.0)
        assert solver.get_excess_rate(inlet, FloatConstraint(_LOW_HEAD_TARGET)) == 0.0

    def test_inside_chart(self, feasibility_solver_setup, compressor, stream_factory):
        """Rate inside chart envelope → excess = 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_LOW_HEAD_INSIDE, pressure_bara=30.0)
        assert solver.get_excess_rate(inlet, FloatConstraint(_LOW_HEAD_TARGET)) == 0.0

    def test_right_of_chart(self, feasibility_solver_setup, compressor, stream_factory):
        """Rate above solver capacity limit → excess > 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_LOW_HEAD_OUTSIDE, pressure_bara=30.0)
        assert solver.get_excess_rate(inlet, FloatConstraint(_LOW_HEAD_TARGET)) > 0.0


class TestRateAxisHighHead:
    """Constant-pressure path at 100 bara (~170 kJ/kg) — sweep rate left to right.

    At h=170 the path lies entirely above the stonewall (highest stonewall head
    133.6 kJ/kg at 11 533 rpm), so the chart envelope is bounded by the surge line
    on the left and the max-speed curve on the right.  Below the left boundary the
    compressor recirculates; above the right boundary it still handles the flow via
    max speed + recirculation, up to the solver capacity limit (~4 702 856 sm³/day).
    """

    def test_left_of_chart(self, feasibility_solver_setup, compressor, stream_factory):
        """Rate below chart envelope (recirculation zone) → excess = 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=500_000.0, pressure_bara=30.0)
        assert solver.get_excess_rate(inlet, FloatConstraint(_HIGH_HEAD_TARGET)) == 0.0

    def test_inside_chart(self, feasibility_solver_setup, compressor, stream_factory):
        """Rate inside chart envelope → excess = 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_HIGH_HEAD_INSIDE, pressure_bara=30.0)
        assert solver.get_excess_rate(inlet, FloatConstraint(_HIGH_HEAD_TARGET)) == 0.0

    def test_right_of_chart(self, feasibility_solver_setup, compressor, stream_factory):
        """Rate above solver capacity limit → excess > 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_HIGH_HEAD_OUTSIDE, pressure_bara=30.0)
        assert solver.get_excess_rate(inlet, FloatConstraint(_HIGH_HEAD_TARGET)) > 0.0


class TestHeadAxisLowRate:
    """Constant-rate path at ~3 500 m³/h — sweep target pressure bottom to top.

    Feasible window: ~49–116 bara.
    Vertical line intersects min-speed curve (7 689 rpm) at 78.5 kJ/kg and surge line
    at 121.1 kJ/kg, giving two recirculation sub-regions:
      left-of-min-speed: 49–~55 bara — compressor recirculates at 7 689 rpm toward stonewall
      left-of-surge:    ~106–116 bara — speeds ≥ 9 886 rpm operate with ASV recirculation
    """

    def test_below_achievable_pressure(self, feasibility_solver_setup, compressor, stream_factory):
        """Target below min achievable (~49 bara) — globally infeasible → excess = full rate."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_LOW_RATE_HEAD_PATH_RATE, pressure_bara=30.0)
        excess = solver.get_excess_rate(inlet, FloatConstraint(_LOW_RATE_HEAD_PATH_BELOW_MIN))
        assert excess == pytest.approx(inlet.standard_rate_sm3_per_day, rel=1e-6)

    def test_left_of_min_speed_curve(self, feasibility_solver_setup, compressor, stream_factory):
        """Target below 7 689 rpm head at this rate — recirculation at min speed → excess = 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_LOW_RATE_HEAD_PATH_RATE, pressure_bara=30.0)
        assert solver.get_excess_rate(inlet, FloatConstraint(_LOW_RATE_HEAD_PATH_LEFT_MIN_SPD)) == 0.0

    def test_inside_chart(self, feasibility_solver_setup, compressor, stream_factory):
        """Target inside natural operating region → excess = 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_LOW_RATE_HEAD_PATH_RATE, pressure_bara=30.0)
        assert solver.get_excess_rate(inlet, FloatConstraint(_LOW_RATE_HEAD_PATH_INSIDE)) == 0.0

    def test_left_of_surge(self, feasibility_solver_setup, compressor, stream_factory):
        """Target above 8 787 rpm region — 9 886+ rpm operate left of surge via ASV → excess = 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_LOW_RATE_HEAD_PATH_RATE, pressure_bara=30.0)
        assert solver.get_excess_rate(inlet, FloatConstraint(_LOW_RATE_HEAD_PATH_LEFT_SURGE)) == 0.0

    def test_above_maximum_achievable(self, feasibility_solver_setup, compressor, stream_factory):
        """Target above max achievable (~116 bara) — globally infeasible → excess = full rate."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_LOW_RATE_HEAD_PATH_RATE, pressure_bara=30.0)
        excess = solver.get_excess_rate(inlet, FloatConstraint(_LOW_RATE_HEAD_PATH_ABOVE_MAX))
        assert excess == pytest.approx(inlet.standard_rate_sm3_per_day, rel=1e-6)


class TestHeadAxisHighRate:
    """Constant-rate path at ~6 000 m³/h — sweep target pressure bottom to top.

    Only speeds ≥ 10 435 rpm can cover 6 000 m³/h (lower speeds are stonewall-limited).
    Feasible window: ~67–101 bara.
    No left-of-surge region: 6 000 m³/h is to the right of all surge points (max 4 328 m³/h).
    No distinct left-of-min-speed region: the lowest feasible speed (10 435 rpm) is already near
    its stonewall at 6 000 m³/h, so its recirculation band merges with the below-achievable boundary.

    Both boundary infeasibilities are rate-conditional (not global): some lower rate IS
    feasible at those pressures, so excess > 0 (partial), not = full rate.
    """

    def test_below_achievable_pressure(self, feasibility_solver_setup, compressor, stream_factory):
        """Target below min achievable at this rate (~67 bara) — rate-conditional → excess > 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_HIGH_RATE_HEAD_PATH_RATE, pressure_bara=30.0)
        assert solver.get_excess_rate(inlet, FloatConstraint(_HIGH_RATE_HEAD_PATH_BELOW_MIN)) > 0.0

    def test_inside_chart(self, feasibility_solver_setup, compressor, stream_factory):
        """Target inside natural operating region → excess = 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_HIGH_RATE_HEAD_PATH_RATE, pressure_bara=30.0)
        assert solver.get_excess_rate(inlet, FloatConstraint(_HIGH_RATE_HEAD_PATH_INSIDE)) == 0.0

    def test_right_of_max_speed_curve(self, feasibility_solver_setup, compressor, stream_factory):
        """Target above 11 533 rpm head at 6 000 m³/h (~101 bara) — lower rate is at max speed
        and can reach the target, so solver returns partial excess > 0."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_HIGH_RATE_HEAD_PATH_RATE, pressure_bara=30.0)
        assert (
            0.0
            < solver.get_excess_rate(inlet, FloatConstraint(_HIGH_RATE_HEAD_PATH_RIGHT_MAX_SPD))
            < inlet.standard_rate_sm3_per_day
        )

    def test_above_maximum_achievable(self, feasibility_solver_setup, compressor, stream_factory):
        """Target above global max achievable (~116 bara) — infeasible at any rate → excess = full rate."""
        solver = feasibility_solver_setup(compressor)
        inlet = stream_factory(standard_rate_m3_per_day=_HIGH_RATE_HEAD_PATH_RATE, pressure_bara=30.0)
        excess = solver.get_excess_rate(inlet, FloatConstraint(_HIGH_RATE_HEAD_PATH_ABOVE_MAX))
        assert excess == pytest.approx(inlet.standard_rate_sm3_per_day, rel=1e-6)


@pytest.fixture
def two_stage_feasibility_solver(
    stage_units_factory,
    process_runner_factory,
    process_pipeline_factory,
    with_individual_asv,
    individual_asv_anti_surge_strategy_factory,
    individual_asv_rate_control_strategy_factory,
    outlet_pressure_solver_factory,
    fluid_service,
):
    """Two identical Unisim stages in series on a shared shaft, with inter-stage cooling."""
    curves = [
        ChartCurve(
            rate_actual_m3_hour=[p[0] for p in pts],
            polytropic_head_joule_per_kg=[_HEAD_CONV(p[1]) for p in pts],
            efficiency_fraction=[p[2] for p in pts],
            speed_rpm=float(speed),
        )
        for speed, pts in _UNISIM_CURVES
    ]
    chart = ChartDataFactory.from_curves(curves)
    c1 = Compressor(
        process_unit_id=ProcessUnitId(ecalc_id_generator()),
        compressor_chart=chart,
        fluid_service=fluid_service,
    )
    c2 = Compressor(
        process_unit_id=ProcessUnitId(ecalc_id_generator()),
        compressor_chart=chart,
        fluid_service=fluid_service,
    )
    shaft = VariableSpeedShaft()
    process_units, loops = with_individual_asv(
        [*stage_units_factory(compressor=c1, shaft=shaft), *stage_units_factory(compressor=c2, shaft=shaft)]
    )
    loop_ids = [loop.get_id() for loop in loops]
    runner = process_runner_factory(units=process_units, configuration_handlers=[shaft, *loops])
    process_pipeline = process_pipeline_factory(units=process_units)
    anti_surge = individual_asv_anti_surge_strategy_factory(
        runner=runner, recirculation_loop_ids=loop_ids, compressors=[c1, c2]
    )
    pressure_control = individual_asv_rate_control_strategy_factory(
        runner=runner, recirculation_loop_ids=loop_ids, compressors=[c1, c2]
    )
    outlet_pressure_solver = outlet_pressure_solver_factory(
        shaft=shaft,
        runner=runner,
        anti_surge_strategy=anti_surge,
        pressure_control_strategy=pressure_control,
        process_pipeline_id=process_pipeline.get_id(),
    )
    return FeasibilitySolver(outlet_pressure_solver=outlet_pressure_solver)


class TestTwoStageTrain:
    """Two identical Unisim stages in series on a shared shaft.

    Inter-stage cooler resets temperature to 303.15 K between stages.
    Each stage has independent ASV recirculation.

    Two-stage operating window (30 bara inlet):
      minimum achievable pressure: ~100 bara
      maximum achievable pressure: ~450 bara
    At 250 bara: capacity ~4 750 000 sm³/day.
    """

    def test_inside(self, two_stage_feasibility_solver, stream_factory):
        """Rate well inside two-stage capacity → excess = 0."""
        inlet = stream_factory(standard_rate_m3_per_day=float(_TWO_STAGE_INSIDE_RATE), pressure_bara=30.0)
        assert two_stage_feasibility_solver.get_excess_rate(inlet, FloatConstraint(_TWO_STAGE_TARGET)) == 0.0

    def test_above_achievable_pressure(self, two_stage_feasibility_solver, stream_factory):
        """Target above two-stage maximum (~450 bara) — infeasible at any rate → excess = full rate."""
        inlet = stream_factory(standard_rate_m3_per_day=float(_TWO_STAGE_INSIDE_RATE), pressure_bara=30.0)
        excess = two_stage_feasibility_solver.get_excess_rate(inlet, FloatConstraint(_TWO_STAGE_ABOVE_MAX_TARGET))
        assert excess == pytest.approx(inlet.standard_rate_sm3_per_day, rel=1e-6)

    def test_rate_exceeds_capacity(self, two_stage_feasibility_solver, stream_factory):
        """Rate above two-stage capacity at 250 bara → excess > 0, < full rate."""
        inlet = stream_factory(standard_rate_m3_per_day=float(_TWO_STAGE_HIGH_RATE), pressure_bara=30.0)
        excess = two_stage_feasibility_solver.get_excess_rate(inlet, FloatConstraint(_TWO_STAGE_TARGET))
        assert 0.0 < excess < inlet.standard_rate_sm3_per_day
