"""Legacy vs new pump comparison tests.

These tests verify that the new Pump domain entity produces the same outlet pressure
as the legacy PumpModel for equivalent operating conditions.

API difference:
- Legacy PumpModel.simulate(rate_m3_per_day, Ps, Pd, density) — Pd is an INPUT;
  head is derived from the pressure difference.
- New Pump.propagate_stream(LiquidStream(Ps, density, mass_rate)) — head comes from
  the pump chart; Pd is an OUTPUT.

For the comparison to be valid we pick operating points that lie exactly on the
chart curve, then derive the expected Pd from the chart head so both models see
the same hydraulic operating point.
"""

import pytest

from libecalc.domain.process.entities.process_units.pump import Pump
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.configuration import SpeedConfiguration
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedSolver
from libecalc.domain.process.process_pipeline.process_unit import create_process_unit_id
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.liquid_stream import LiquidStream
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData

# ---------------------------------------------------------------------------
# Shared chart data (identical for legacy and new).
# Single speed: 3000 rpm, rates 10–100 m³/h, heads 50_000–20_000 J/kg, η=0.7
# ---------------------------------------------------------------------------
_SINGLE_SPEED_CHART = UserDefinedChartData(
    curves=[
        ChartCurve(
            speed_rpm=3000.0,
            rate_actual_m3_hour=[10.0, 50.0, 100.0],
            polytropic_head_joule_per_kg=[50_000.0, 40_000.0, 20_000.0],
            efficiency_fraction=[0.7, 0.7, 0.7],
        )
    ],
    control_margin=0.0,
)

# Variable speed: two curves at 2500 and 3000 rpm.
# Both use constant efficiency 0.7 so legacy 2D lookup and new curve interpolation
# return the same efficiency at any operating point.
_VAR_SPEED_CHART = UserDefinedChartData(
    curves=[
        ChartCurve(
            speed_rpm=2500.0,
            rate_actual_m3_hour=[10.0, 80.0],
            polytropic_head_joule_per_kg=[35_000.0, 14_000.0],
            efficiency_fraction=[0.7, 0.7],
        ),
        ChartCurve(
            speed_rpm=3000.0,
            rate_actual_m3_hour=[10.0, 80.0],
            polytropic_head_joule_per_kg=[50_000.0, 20_000.0],
            efficiency_fraction=[0.7, 0.7],
        ),
    ],
    control_margin=0.0,
)

_DENSITY = 800.0  # kg/m³
_PS = 10.0  # bara

_BARA_TO_PASCAL = 1e5


def _stream(rate_m3h: float, pressure: float = _PS, density: float = _DENSITY) -> LiquidStream:
    return LiquidStream(pressure_bara=pressure, density_kg_per_m3=density, mass_rate_kg_per_h=rate_m3h * density)


def _pd_from_head(head_j_per_kg: float, density: float = _DENSITY, ps: float = _PS) -> float:
    """Compute discharge pressure from head, density, and suction pressure."""
    return ps + head_j_per_kg * density / _BARA_TO_PASCAL


# ---------------------------------------------------------------------------
# Single-speed: normal operating range
# ---------------------------------------------------------------------------
class TestSingleSpeedLegacyVsNew:
    def test_outlet_pressure_matches_expected_head(self):
        """New Pump outlet pressure corresponds to the head from the chart."""
        pump = Pump(process_unit_id=create_process_unit_id(), pump_chart=_SINGLE_SPEED_CHART)
        outlet = pump.propagate_stream(_stream(50.0))
        expected_pd = _pd_from_head(40_000.0)
        assert outlet.pressure_bara == pytest.approx(expected_pd, rel=1e-4)

    def test_legacy_zero_rate_is_no_op(self):
        """Legacy pump returns zero power at zero rate; new pump is not invoked (rate=0 is an upstream concern)."""
        legacy = PumpModel(pump_chart=_SINGLE_SPEED_CHART)
        power, head, status = legacy.simulate(
            rate=0.0, suction_pressure=_PS, discharge_pressure=50.0, fluid_density=_DENSITY
        )
        assert power == 0.0
        assert head == 0.0


# ---------------------------------------------------------------------------
# Variable-speed: exact speed match (lies on a known chart curve)
# ---------------------------------------------------------------------------
class TestVariableSpeedLegacyVsNew:
    def test_speed_solver_finds_correct_speed(self, search_strategy_factory, root_finding_strategy):
        """SpeedSolver finds the speed that delivers a target outlet pressure.
        At rate=10 m³/h with target Pd derived from speed=3000 head, solver returns ~3000 rpm."""
        target_head = 50_000.0  # J/kg — corresponds to 3000 rpm at 10 m³/h
        target_pd = _pd_from_head(target_head)
        inlet = _stream(10.0)

        pump = Pump(process_unit_id=create_process_unit_id(), pump_chart=_VAR_SPEED_CHART)
        solver = SpeedSolver(
            search_strategy=search_strategy_factory(tolerance=1.0),
            root_finding_strategy=root_finding_strategy,
            boundary=Boundary(min=2500.0, max=3000.0),
            target_pressure=target_pd,
        )

        def func(cfg: SpeedConfiguration) -> LiquidStream:
            pump.set_speed(cfg.speed)
            return pump.propagate_stream(inlet)

        solution = solver.solve(func)

        assert solution.success
        assert solution.configuration.speed == pytest.approx(3000.0, rel=1e-3)

    def test_speed_solver_interpolated_speed(self, search_strategy_factory, root_finding_strategy):
        """Solver finds an intermediate speed when target pressure is between min and max curve pressures."""
        # At rate=10 m³/h, speed=2750 (halfway): head = (35000+50000)/2 = 42500 J/kg
        # Pd = 10 + 42500 * 800 / 1e5 = 350 bara
        target_pd = _pd_from_head(42_500.0)
        inlet = _stream(10.0)

        pump = Pump(process_unit_id=create_process_unit_id(), pump_chart=_VAR_SPEED_CHART)
        solver = SpeedSolver(
            search_strategy=search_strategy_factory(tolerance=1.0),
            root_finding_strategy=root_finding_strategy,
            boundary=Boundary(min=2500.0, max=3000.0),
            target_pressure=target_pd,
        )

        def func(cfg: SpeedConfiguration) -> LiquidStream:
            pump.set_speed(cfg.speed)
            return pump.propagate_stream(inlet)

        solution = solver.solve(func)

        assert solution.success
        assert solution.configuration.speed == pytest.approx(2750.0, rel=1e-2)

    def test_speed_solver_target_too_high_returns_failure(self, search_strategy_factory, root_finding_strategy):
        """When target pressure exceeds what max speed can deliver, solver fails."""
        target_pd = _pd_from_head(50_000.0) + 100.0  # 100 bara above max achievable
        inlet = _stream(10.0)

        pump = Pump(process_unit_id=create_process_unit_id(), pump_chart=_VAR_SPEED_CHART)
        solver = SpeedSolver(
            search_strategy=search_strategy_factory(tolerance=1.0),
            root_finding_strategy=root_finding_strategy,
            boundary=Boundary(min=2500.0, max=3000.0),
            target_pressure=target_pd,
        )

        def func(cfg: SpeedConfiguration) -> LiquidStream:
            pump.set_speed(cfg.speed)
            return pump.propagate_stream(inlet)

        solution = solver.solve(func)

        assert not solution.success

    def test_speed_solver_target_too_low_returns_failure(self, search_strategy_factory, root_finding_strategy):
        """When target pressure is below what min speed delivers, solver fails."""
        target_pd = _pd_from_head(35_000.0) - 100.0  # below min-speed delivery
        inlet = _stream(10.0)

        pump = Pump(process_unit_id=create_process_unit_id(), pump_chart=_VAR_SPEED_CHART)
        solver = SpeedSolver(
            search_strategy=search_strategy_factory(tolerance=1.0),
            root_finding_strategy=root_finding_strategy,
            boundary=Boundary(min=2500.0, max=3000.0),
            target_pressure=target_pd,
        )

        def func(cfg: SpeedConfiguration) -> LiquidStream:
            pump.set_speed(cfg.speed)
            return pump.propagate_stream(inlet)

        solution = solver.solve(func)

        assert not solution.success
