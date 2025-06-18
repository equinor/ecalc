import pytest

from libecalc.domain.common.entity_id import SimpleEntityID
from libecalc.domain.process.entities.process_units.choke_valve import ChokeValve
from libecalc.domain.process.entities.process_units.choke_valve.exceptions import InvalidPressureDropException
from libecalc.domain.process.entities.process_units.port_names import SingleIO


def test_single_choke_valve_pressure_drop(fluid_stream_mock):
    """Test basic choke valve pressure drop calculation."""
    valve = ChokeValve(SimpleEntityID("tv-1"), delta_p_bar=5.0)
    # Use the constant for robustness
    valve.connect_inlet_port(SingleIO.INLET, fluid_stream_mock)
    valve.calculate()

    outlet_stream = valve.get_outlet_stream()
    assert outlet_stream.pressure_bara == pytest.approx(fluid_stream_mock.pressure_bara - 5.0)


def test_choke_valve_invalid_pressure_drop(fluid_stream_mock):
    """Test that InvalidPressureDropException is raised when inlet pressure is lower than delta_p."""
    # fluid_stream_mock has 20.0 bara pressure, create valve with 100 bar pressure drop
    valve = ChokeValve(SimpleEntityID("tv-1"), delta_p_bar=100.0)

    # Should raise InvalidPressureDropException when trying to connect
    with pytest.raises(InvalidPressureDropException) as exc_info:
        valve.connect_inlet_port(SingleIO.INLET, fluid_stream_mock)

    # Verify the exception contains relevant information
    assert "20.00 bara" in str(exc_info.value)  # inlet pressure
    assert "100.00 bar" in str(exc_info.value)  # pressure drop
    assert "negative pressure not allowed" in str(exc_info.value)
