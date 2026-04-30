from ecalc_neqsim_wrapper.thermo import STANDARD_PRESSURE_BARA, STANDARD_TEMPERATURE_KELVIN


def test_set_temperature(fluid_model_medium, fluid_service, temperature_setter_factory):
    inlet_stream = fluid_service.create_stream_from_standard_rate(
        fluid_model=fluid_model_medium,
        pressure_bara=STANDARD_PRESSURE_BARA,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        standard_rate_m3_per_day=100000,
    )
    temperature_setter = temperature_setter_factory(required_temperature_kelvin=273.15)
    outlet_stream = temperature_setter.propagate_stream(inlet_stream)

    assert inlet_stream.temperature_kelvin == STANDARD_TEMPERATURE_KELVIN
    assert outlet_stream.temperature_kelvin == 273.15
