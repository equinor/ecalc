from ecalc_neqsim_wrapper.thermo import STANDARD_TEMPERATURE_KELVIN, STANDARD_PRESSURE_BARA
from libecalc.domain.process.entities.process_units.rate_modifier.rate_modifier import RateModifier


def test_modify_rate(fluid_factory_medium):
    inlet_stream = fluid_factory_medium.create_stream_from_mass_rate(
        pressure_bara=STANDARD_PRESSURE_BARA,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        mass_rate_kg_per_h=100000,
    )
    rate_modifier = RateModifier(
        recirculation_mass_rate=50000,
    )
    middle_stream = rate_modifier.add_rate(inlet_stream)
    assert middle_stream.mass_rate_kg_per_h == 150000

    end_stream = rate_modifier.remove_rate(middle_stream)
    assert end_stream.mass_rate_kg_per_h == 100000
