import pytest

from libecalc.domain.common.entity_id import SimpleEntityID
from libecalc.domain.process.entities.process_units.choke_valve import ChokeValve
from libecalc.domain.process.entities.process_units.port_names import SingleIO


def test_single_choke_valve_pressure_drop(fluid_stream_mock):
    """Test basic choke valve pressure drop calculation."""
    valve = ChokeValve(SimpleEntityID("tv-1"), delta_p_bar=5.0)
    # Use the constant for robustness
    valve.connect_inlet_port(SingleIO.INLET, fluid_stream_mock)
    valve.calculate()

    outlet_stream = valve.outlet_stream
    assert outlet_stream.pressure_bara == pytest.approx(fluid_stream_mock.pressure_bara - 5.0)
