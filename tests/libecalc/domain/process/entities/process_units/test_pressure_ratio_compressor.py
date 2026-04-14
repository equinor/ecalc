import pytest

from libecalc.domain.process.entities.process_units.pressure_ratio_compressor import PressureRatioCompressor
from libecalc.domain.process.process_system.process_unit import create_process_unit_id
from libecalc.testing.chart_data_factory import ChartDataFactory


@pytest.fixture
def compressor(fluid_service):
    chart_data = ChartDataFactory.from_rate_and_head(
        rate=[300.0, 1200.0],
        head=[80000.0, 55000.0],
        efficiency=0.75,
    )
    return PressureRatioCompressor(
        process_unit_id=create_process_unit_id(),
        compressor_chart=chart_data,
        fluid_service=fluid_service,
    )


def test_outlet_pressure_equals_inlet_times_ratio(stream_factory, compressor):
    """Outlet pressure must be exactly inlet * pressure_ratio."""
    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)

    outlet = compressor.propagate_stream_at_pressure_ratio(inlet, pressure_ratio=3.0)

    assert outlet.pressure_bara == pytest.approx(inlet.pressure_bara * 3.0, rel=1e-6)


def test_outlet_temperature_higher_than_inlet(stream_factory, compressor):
    """Compression raises temperature — outlet must be hotter than inlet."""
    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)

    outlet = compressor.propagate_stream_at_pressure_ratio(inlet, pressure_ratio=3.0)

    assert outlet.temperature_kelvin > inlet.temperature_kelvin


def test_rate_is_conserved(stream_factory, compressor):
    """Standard rate is conserved through the compressor."""
    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)

    outlet = compressor.propagate_stream_at_pressure_ratio(inlet, pressure_ratio=3.0)

    assert outlet.standard_rate_sm3_per_day == pytest.approx(inlet.standard_rate_sm3_per_day, rel=1e-6)


def test_pressure_ratio_one_is_identity(stream_factory, compressor):
    """A pressure ratio of 1.0 should leave pressure unchanged."""
    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)

    outlet = compressor.propagate_stream_at_pressure_ratio(inlet, pressure_ratio=1.0)

    assert outlet.pressure_bara == pytest.approx(inlet.pressure_bara, rel=1e-6)


def test_propagate_stream_raises_not_implemented(stream_factory, compressor):
    """propagate_stream() is not supported — a pressure ratio is always required."""
    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)

    with pytest.raises(NotImplementedError):
        compressor.propagate_stream(inlet)
