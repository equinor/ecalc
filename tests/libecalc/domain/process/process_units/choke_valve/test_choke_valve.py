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


def test_choked_flow_handling(fluid_stream_mock, monkeypatch):
    """Test that choke valve correctly handles choked flow by limiting outlet pressure."""
    from unittest.mock import patch

    # Based on the mock fluid_stream's kappa of 1.3
    # Critical pressure ratio = (2/(1.3+1))^(1.3/(1.3-1)) ≈ 0.546
    # For inlet pressure of 20 bara, critical pressure is about 10.92 bara
    # Set a pressure drop that would cause outlet pressure to go below critical pressure
    # if not limited (20 bara - 15 bara = 5 bara, which is below critical ~10.92 bara)
    valve = ChokeValve(SimpleEntityID("choked-valve"), delta_p_bar=15.0)

    # Calculate critical pressure ratio for verification
    kappa = fluid_stream_mock.kappa
    pressure_ratio_crit = (2 / (kappa + 1)) ** (kappa / (kappa - 1))
    expected_critical_pressure = fluid_stream_mock.pressure_bara * pressure_ratio_crit

    # Patch the logger to capture the warning
    with patch("libecalc.domain.process.entities.process_units.choke_valve.choke_valve.logger") as mock_logger:
        valve.connect_inlet_port(SingleIO.INLET, fluid_stream_mock)
        valve.calculate()

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "Choked flow condition met" in warning_msg

    # Get the outlet stream and verify pressure
    outlet_stream = valve.get_outlet_stream()

    # Outlet pressure should be limited to the critical pressure
    assert outlet_stream.pressure_bara == pytest.approx(expected_critical_pressure, abs=0.01)
    # This should be higher than the naively calculated outlet pressure (20 - 15 = 5 bara)
    assert outlet_stream.pressure_bara > 5.0
