from ecalc_neqsim_wrapper.thermo import STANDARD_PRESSURE_BARA, STANDARD_TEMPERATURE_KELVIN
from libecalc.domain.process.entities.process_units.rate_modifier.rate_modifier import RateModifier
from libecalc.domain.process.entities.shaft import VariableSpeedShaft


def test_modify_rate(variable_speed_compressor_chart_data, fluid_model_medium, fluid_service):
    inlet_stream = fluid_service.create_stream_from_mass_rate(
        fluid_model=fluid_model_medium,
        pressure_bara=STANDARD_PRESSURE_BARA,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        mass_rate_kg_per_h=100000,
    )
    rate_modifier = RateModifier(variable_speed_compressor_chart_data, shaft=VariableSpeedShaft())
    rate_modifier.mass_rate_to_recirculate = 50000
    middle_stream = rate_modifier.add_rate(inlet_stream)
    assert middle_stream.mass_rate_kg_per_h == 150000

    end_stream = rate_modifier.remove_rate(middle_stream)
    assert end_stream.mass_rate_kg_per_h == 100000
