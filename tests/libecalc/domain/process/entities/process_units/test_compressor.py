import pytest

from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.domain.process.process_pipeline.process_unit import create_process_unit_id


@pytest.fixture
def shaft():
    return VariableSpeedShaft()


@pytest.fixture
def compressor(shaft, variable_speed_compressor_chart_data, fluid_service):
    """A Compressor backed by the standard variable-speed chart from conftest."""
    compressor = Compressor(
        process_unit_id=create_process_unit_id(),
        compressor_chart=variable_speed_compressor_chart_data,
        fluid_service=fluid_service,
    )
    shaft.connect(compressor)
    return compressor


def _inlet_at_midpoint(stream_factory, compressor, pressure_bara=30.0, temperature_kelvin=300.0):
    """Return a stream at the midpoint between min and max standard rate for the current speed."""
    placeholder = stream_factory(
        standard_rate_m3_per_day=1.0, pressure_bara=pressure_bara, temperature_kelvin=temperature_kelvin
    )
    min_rate = compressor.get_minimum_standard_rate(placeholder)
    max_rate = compressor.get_maximum_standard_rate(placeholder)
    rate = (min_rate + max_rate) / 2
    return stream_factory(
        standard_rate_m3_per_day=rate, pressure_bara=pressure_bara, temperature_kelvin=temperature_kelvin
    )


class TestCompressorSpeedBoundary:
    def test_speed_boundary_matches_chart(self, compressor, shaft):
        boundary = shaft.get_speed_boundary()
        assert boundary.min > 0
        assert boundary.max > boundary.min


class TestCompressorFlowLimits:
    def test_raises_rate_too_low_below_minimum_flow(self, stream_factory, compressor, shaft):
        shaft.set_speed(shaft.get_speed_boundary().min)
        inlet = stream_factory(standard_rate_m3_per_day=1.0, pressure_bara=30.0, temperature_kelvin=300.0)
        with pytest.raises(RateTooLowError):
            compressor.propagate_stream(inlet_stream=inlet)

    def test_raises_rate_too_high_above_maximum_flow(self, stream_factory, compressor, shaft):
        shaft.set_speed(shaft.get_speed_boundary().max)
        inlet = stream_factory(standard_rate_m3_per_day=1e12, pressure_bara=30.0, temperature_kelvin=300.0)
        with pytest.raises(RateTooHighError):
            compressor.propagate_stream(inlet_stream=inlet)


class TestCompressorPropagation:
    def test_outlet_pressure_higher_than_inlet(self, stream_factory, compressor, shaft):
        speed = (shaft.get_speed_boundary().min + shaft.get_speed_boundary().max) / 2
        shaft.set_speed(speed)
        inlet = _inlet_at_midpoint(stream_factory, compressor)
        outlet = compressor.propagate_stream(inlet_stream=inlet)
        assert outlet.pressure_bara > inlet.pressure_bara

    def test_higher_speed_gives_higher_outlet_pressure(self, stream_factory, compressor, shaft):
        boundary = shaft.get_speed_boundary()

        shaft.set_speed(boundary.min * 1.05)
        inlet_low = _inlet_at_midpoint(stream_factory, compressor)
        outlet_low = compressor.propagate_stream(inlet_stream=inlet_low)

        shaft.set_speed(boundary.max * 0.95)
        inlet_high = _inlet_at_midpoint(stream_factory, compressor)
        outlet_high = compressor.propagate_stream(inlet_stream=inlet_high)

        assert outlet_high.pressure_bara > outlet_low.pressure_bara

    def test_standard_rate_is_conserved(self, stream_factory, compressor, shaft):
        speed = (shaft.get_speed_boundary().min + shaft.get_speed_boundary().max) / 2
        shaft.set_speed(speed)
        inlet = _inlet_at_midpoint(stream_factory, compressor)
        outlet = compressor.propagate_stream(inlet_stream=inlet)
        assert outlet.standard_rate_sm3_per_day == pytest.approx(inlet.standard_rate_sm3_per_day, rel=1e-6)


class TestCompressorRecirculationRange:
    def test_recirculation_range_min_is_zero_when_above_surge(self, stream_factory, compressor, shaft):
        """When the inlet rate is comfortably above surge, no recirculation is needed."""
        speed = (shaft.get_speed_boundary().min + shaft.get_speed_boundary().max) / 2
        shaft.set_speed(speed)
        inlet = _inlet_at_midpoint(stream_factory, compressor)
        boundary = compressor.get_recirculation_range(inlet_stream=inlet)
        assert boundary.min == pytest.approx(0.0)

    def test_recirculation_range_min_positive_when_below_surge(self, stream_factory, compressor, shaft):
        """When inlet rate is below the surge limit, min recirculation must be > 0."""
        shaft.set_speed(shaft.get_speed_boundary().max * 0.9)
        placeholder = stream_factory(standard_rate_m3_per_day=1.0, pressure_bara=30.0, temperature_kelvin=300.0)
        min_rate = compressor.get_minimum_standard_rate(placeholder)
        inlet = stream_factory(
            standard_rate_m3_per_day=min_rate * 0.5,
            pressure_bara=30.0,
            temperature_kelvin=300.0,
        )
        boundary = compressor.get_recirculation_range(inlet_stream=inlet)
        assert boundary.min > 0.0
