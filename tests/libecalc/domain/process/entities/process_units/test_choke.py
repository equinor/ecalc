from ecalc_neqsim_wrapper.thermo import STANDARD_TEMPERATURE_KELVIN
from libecalc.domain.process.entities.process_units.choke import Choke


def test_modify_pressure(fluid_model_medium, fluid_service):
    inlet_stream = fluid_service.create_stream_from_standard_rate(
        fluid_model=fluid_model_medium,
        pressure_bara=20.0,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        standard_rate_m3_per_day=100000,
    )
    choke = Choke(pressure_change=10.0, fluid_service=fluid_service)
    outlet_stream = choke.propagate_stream(inlet_stream)

    assert inlet_stream.pressure_bara == 20.0
    assert outlet_stream.pressure_bara == 10.0
