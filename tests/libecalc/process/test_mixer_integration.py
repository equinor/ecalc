from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.ecalc_model.time_series_configuration import (
    TimeSeriesMixerConfiguration,
    TimeSeriesTemperatureSetterConfiguration,
)
from libecalc.process.process_solver.process_pipeline_runner import propagate_stream_many
from libecalc.process.shaft import Shaft
from libecalc.testing.process_builders import (
    YamlCompressorBuilder,
    YamlIndividualStreamDistributionBuilder,
    YamlMixerBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    YamlTemperatureSetterBuilder,
)

PERIOD = Period(start=datetime(2020, 1, 1), end=datetime(2030, 1, 1))


def test_yaml_mixer_maps_to_runnable_pipeline(process_simulation_mapper, fluid_service):
    """
    Verify that a Mixer defined in YAML survives the full chain:
    YAML → mapper → runtime configuration → pipeline execution.

    Complements test_mixer_splitter.py (which tests Mixer in isolation)
    by proving the mapper wires it correctly into a runnable pipeline.
    """

    # -- Build YAML --
    yaml_mixer = YamlMixerBuilder().with_test_data().validate()
    yaml_pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train_with_mixer")
        .with_item(name="temp_setter_1", target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .with_item(name="compressor_1", target=YamlCompressorBuilder().with_test_data().validate())
        .with_item(target=yaml_mixer)
        .with_item(name="temp_setter_2", target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .with_item(name="compressor_2", target=YamlCompressorBuilder().with_test_data().validate())
        .validate()
    )

    yaml_simulation = (
        YamlProcessSimulationBuilder()
        .with_name("mixer_test")
        .with_pipeline(yaml_pipeline)
        .with_stream_distribution(YamlIndividualStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )

    # -- Map to process domain objects --
    pipelines, simulation = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_simulation,
        process_periods=[PERIOD],
    )

    units = pipelines[0].get_process_units()
    problem = simulation.process_problems[0]
    pipeline_id = problem.process_pipeline_id
    configs = simulation.process_configurations[pipeline_id]

    # -- Configure units
    shaft = next(h for h in problem.configuration_handlers if isinstance(h, Shaft))
    shaft.set_speed(10000)

    for unit_id, config in configs.items():
        unit = next(u for u in units if u.get_id() == unit_id)
        match config:
            case TimeSeriesTemperatureSetterConfiguration():
                unit.set_temperature(Unit.CELSIUS.to(Unit.KELVIN)(config.temperature_in_celsius.get_masked_values()[0]))
            case TimeSeriesMixerConfiguration():
                ts = config.sidestream
                unit.set_stream(
                    fluid_service.create_stream_from_standard_rate(
                        fluid_model=ts.fluid_model,
                        pressure_bara=ts.pressure_bara.get_masked_values()[0],
                        temperature_kelvin=ts.temperature_kelvin.get_masked_values()[0],
                        standard_rate_m3_per_day=ts.standard_rate_m3_per_day.get_stream_day_values()[0],
                    )
                )

    # -- Run pipeline --
    inlet_stream = fluid_service.create_stream_from_standard_rate(
        fluid_model=simulation.get_inlet_streams()[0].fluid_model,
        pressure_bara=20.0,
        temperature_kelvin=303.15,
        standard_rate_m3_per_day=2_000_000,
    )

    outlet = propagate_stream_many(units, inlet_stream)

    sidestream_rate_sm3_per_day = yaml_mixer.sidestream.rate.value
    expected_sidestream_mass_rate = fluid_service.standard_rate_to_mass_rate(
        fluid_model=simulation.get_inlet_streams()[0].fluid_model,
        standard_rate_m3_per_day=sidestream_rate_sm3_per_day,
    )

    # -- Assert: mass is conserved — compressors and temperature setters
    # change P and T but not mass rate, so outlet = inlet + sidestream --
    assert outlet.mass_rate_kg_per_h == inlet_stream.mass_rate_kg_per_h + expected_sidestream_mass_rate
