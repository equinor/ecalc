import pytest

from tests.libecalc.process.process_units import test_compressor

_inlet_at_midpoint = test_compressor._inlet_at_midpoint
compressor = test_compressor.compressor
shaft = test_compressor.shaft


def test_properties_populated_after_propagation(stream_factory, compressor, shaft):
    speed = (shaft.get_speed_boundary().min + shaft.get_speed_boundary().max) / 2
    shaft.set_speed(speed)
    inlet = _inlet_at_midpoint(stream_factory, compressor)
    compressor.propagate_stream(inlet_stream=inlet)

    assert compressor.polytropic_head_joule_per_kg > 0
    assert 0 < compressor.polytropic_efficiency <= 1.0
    assert compressor.enthalpy_change_joule_per_kg > 0
    assert compressor.power_megawatt > 0
    assert compressor.actual_rate_m3_per_hour == pytest.approx(inlet.volumetric_rate_m3_per_hour)


def test_power_is_consistent_with_stream_enthalpy_change_and_mass_rate(stream_factory, compressor, shaft):
    speed = (shaft.get_speed_boundary().min + shaft.get_speed_boundary().max) / 2
    shaft.set_speed(speed)
    inlet = _inlet_at_midpoint(stream_factory, compressor)
    outlet = compressor.propagate_stream(inlet_stream=inlet)

    expected_enthalpy_change = outlet.enthalpy_joule_per_kg - inlet.enthalpy_joule_per_kg
    expected_power = expected_enthalpy_change * inlet.mass_rate_kg_per_h / 1e6 / 3600
    assert compressor.enthalpy_change_joule_per_kg == pytest.approx(expected_enthalpy_change, rel=1e-6)
    assert compressor.power_megawatt == pytest.approx(expected_power, rel=1e-6)


@pytest.mark.parametrize(
    "property_name",
    [
        "polytropic_head_joule_per_kg",
        "polytropic_efficiency",
        "enthalpy_change_joule_per_kg",
        "power_megawatt",
        "actual_rate_m3_per_hour",
    ],
)
def test_properties_raise_before_propagation(compressor, property_name):
    with pytest.raises(ValueError, match="propagate_stream"):
        getattr(compressor, property_name)
