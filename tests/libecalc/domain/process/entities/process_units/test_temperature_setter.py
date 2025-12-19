from uuid import uuid4

from ecalc_neqsim_wrapper.thermo import STANDARD_TEMPERATURE_KELVIN, STANDARD_PRESSURE_BARA
from libecalc.domain.process.entities.process_units.temperature_setter.temperature_setter import TemperatureSetter


def test_set_temperature(fluid_factory_medium):
    inlet_stream = fluid_factory_medium.create_stream_from_standard_rate(
        pressure_bara=STANDARD_PRESSURE_BARA,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        standard_rate_m3_per_day=100000,
    )
    temperature_setter = TemperatureSetter(required_temperature_kelvin=273.15, unit_id=uuid4())
    outlet_stream = temperature_setter.set_temperature(inlet_stream)

    assert inlet_stream.temperature_kelvin == STANDARD_TEMPERATURE_KELVIN
    assert outlet_stream.temperature_kelvin == 273.15
