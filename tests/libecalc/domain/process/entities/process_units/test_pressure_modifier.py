from ecalc_neqsim_wrapper.thermo import STANDARD_TEMPERATURE_KELVIN
from libecalc.domain.process.entities.process_units.pressure_modifier.pressure_modifier import (
    DifferentialPressureModifier,
)


def test_modify_pressure(fluid_factory_medium):
    inlet_stream = fluid_factory_medium.create_stream_from_standard_rate(
        pressure_bara=20.0,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        standard_rate_m3_per_day=100000,
    )
    modifier = DifferentialPressureModifier(differential_pressure=10.0)
    outlet_stream = modifier.modify_pressure(inlet_stream)

    assert inlet_stream.pressure_bara == 20.0
    assert outlet_stream.pressure_bara == 10.0
