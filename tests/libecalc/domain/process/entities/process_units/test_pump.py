import pytest

from libecalc.domain.process.entities.process_units.pump import Pump
from libecalc.domain.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.domain.process.process_pipeline.process_unit import create_process_unit_id
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.liquid_stream import LiquidStream
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData

# Pump chart: one single-speed curve at 3000 rpm
# rate [m³/h]: 10 → 100, head [J/kg]: 50_000 → 20_000, efficiency: 0.7 constant
_SINGLE_SPEED_CURVE = ChartCurve(
    speed_rpm=3000.0,
    rate_actual_m3_hour=[10.0, 50.0, 100.0],
    polytropic_head_joule_per_kg=[50_000.0, 40_000.0, 20_000.0],
    efficiency_fraction=[0.7, 0.7, 0.7],
)

_SINGLE_SPEED_CHART = UserDefinedChartData(curves=[_SINGLE_SPEED_CURVE], control_margin=0.0)

# Variable-speed chart: two curves at 2500 and 3000 rpm
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


def _make_pump(chart=_SINGLE_SPEED_CHART) -> Pump:
    return Pump(process_unit_id=create_process_unit_id(), pump_chart=chart)


def _stream(rate_m3h: float = 50.0, pressure: float = 10.0, density: float = 800.0) -> LiquidStream:
    """Liquid stream: mass_rate from volumetric rate × density."""
    return LiquidStream(
        pressure_bara=pressure,
        density_kg_per_m3=density,
        mass_rate_kg_per_h=rate_m3h * density,
    )


class TestLiquidStream:
    def test_volumetric_rate(self):
        stream = _stream(rate_m3h=50.0, density=800.0)
        assert stream.volumetric_rate_m3_per_hour == pytest.approx(50.0)

    def test_with_pressure(self):
        stream = _stream(pressure=10.0)
        updated = stream.with_pressure(50.0)
        assert updated.pressure_bara == 50.0
        assert updated.density_kg_per_m3 == stream.density_kg_per_m3
        assert updated.mass_rate_kg_per_h == stream.mass_rate_kg_per_h

    def test_negative_mass_rate_raises(self):
        with pytest.raises(ValueError):
            LiquidStream(pressure_bara=10.0, density_kg_per_m3=800.0, mass_rate_kg_per_h=-1.0)

    def test_zero_density_raises(self):
        with pytest.raises(ValueError):
            LiquidStream(pressure_bara=10.0, density_kg_per_m3=0.0, mass_rate_kg_per_h=1000.0)


class TestPumpSingleSpeed:
    def test_outlet_pressure_increases(self):
        """Pump adds pressure — outlet must be above inlet."""
        pump = _make_pump()
        inlet = _stream(rate_m3h=50.0, pressure=10.0, density=800.0)
        outlet = pump.propagate_stream(inlet)
        assert outlet.pressure_bara > inlet.pressure_bara

    def test_outlet_pressure_formula(self):
        """P_out = P_in + head × density / 1e5."""
        pump = _make_pump()
        inlet = _stream(rate_m3h=50.0, pressure=10.0, density=800.0)
        # head at 50 m³/h = 40_000 J/kg (from chart)
        expected_pressure_rise = 40_000.0 * 800.0 / 1e5  # = 320 bara
        outlet = pump.propagate_stream(inlet)
        assert outlet.pressure_bara == pytest.approx(10.0 + expected_pressure_rise, rel=1e-3)

    def test_density_and_mass_rate_unchanged(self):
        """Pump does not change fluid density or mass rate."""
        pump = _make_pump()
        inlet = _stream(rate_m3h=50.0, density=800.0)
        outlet = pump.propagate_stream(inlet)
        assert outlet.density_kg_per_m3 == inlet.density_kg_per_m3
        assert outlet.mass_rate_kg_per_h == inlet.mass_rate_kg_per_h

    def test_below_minimum_rate_raises(self):
        """Below minimum flow: pump raises RateTooLowError (recirc is handled externally)."""
        pump = _make_pump()
        inlet = _stream(rate_m3h=1.0)  # well below chart minimum of 10 m³/h
        with pytest.raises(RateTooLowError):
            pump.propagate_stream(inlet)

    def test_above_maximum_rate_raises(self):
        pump = _make_pump()
        inlet = _stream(rate_m3h=200.0)  # above max of 100 m³/h
        with pytest.raises(RateTooHighError):
            pump.propagate_stream(inlet)

    def test_no_speed_needed_for_single_speed(self):
        """Single-speed pump: set_speed() not required."""
        pump = _make_pump()
        inlet = _stream(rate_m3h=50.0)
        outlet = pump.propagate_stream(inlet)  # should not raise
        assert outlet.pressure_bara > inlet.pressure_bara


class TestPumpVariableSpeed:
    def test_exact_speed_match(self):
        """At exact chart speed, head is taken directly from that curve."""
        pump = _make_pump(_VAR_SPEED_CHART)
        pump.set_speed(3000.0)
        inlet = _stream(rate_m3h=10.0, pressure=5.0, density=800.0)
        outlet = pump.propagate_stream(inlet)
        # head at rate=10, speed=3000 = 50_000 J/kg
        expected_rise = 50_000.0 * 800.0 / 1e5
        assert outlet.pressure_bara == pytest.approx(5.0 + expected_rise, rel=1e-3)

    def test_interpolated_speed(self):
        """At speed halfway between curves, head is linearly interpolated."""
        pump = _make_pump(_VAR_SPEED_CHART)
        pump.set_speed(2750.0)  # halfway between 2500 and 3000
        inlet = _stream(rate_m3h=10.0, pressure=5.0, density=800.0)
        outlet = pump.propagate_stream(inlet)
        # head at rate=10: 35_000 (2500rpm) and 50_000 (3000rpm), alpha=0.5 → 42_500
        expected_rise = 42_500.0 * 800.0 / 1e5
        assert outlet.pressure_bara == pytest.approx(5.0 + expected_rise, rel=1e-3)

    def test_missing_speed_raises(self):
        """Variable-speed pump without set_speed() raises on propagate_stream()."""
        pump = _make_pump(_VAR_SPEED_CHART)
        with pytest.raises(ValueError, match="Speed not set"):
            pump.propagate_stream(_stream())
