from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.ecalc_model.time_series_configuration import (
    TimeSeriesSplitterConfiguration,
    TimeSeriesTemperatureSetterConfiguration,
)
from libecalc.process.process_solver.process_pipeline_runner import propagate_stream_many
from libecalc.process.shaft import Shaft
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompressorBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    YamlSplitterBuilder,
    YamlTemperatureSetterBuilder,
)

PERIOD = Period(start=datetime(2020, 1, 1), end=datetime(2030, 1, 1))


def test_yaml_splitter_maps_to_runnable_pipeline(process_simulation_mapper, fluid_service):
    """Verify that a Splitter defined in YAML survives the full chain:
    YAML → mapper → runtime configuration → pipeline execution.

    Complements test_mixer_splitter.py (which tests Splitter in isolation)
    by proving the mapper wires it correctly into a runnable pipeline.
    """

    # -- Build YAML --
    yaml_splitter = YamlSplitterBuilder().with_test_data().validate()
    yaml_pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train_with_splitter")
        .with_items(
            [
                YamlTemperatureSetterBuilder().with_name("temp_setter_1").with_test_data().validate(),
                YamlCompressorBuilder().with_name("compressor_1").with_test_data().validate(),
                yaml_splitter,
                YamlTemperatureSetterBuilder().with_name("temp_setter_2").with_test_data().validate(),
                YamlCompressorBuilder().with_name("compressor_2").with_test_data().validate(),
            ]
        )
        .validate()
    )
    yaml_simulation = (
        YamlProcessSimulationBuilder()
        .with_name("splitter_test")
        .with_pipeline(yaml_pipeline)
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )

    # -- Map to domain objects --
    pipelines, simulation = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_simulation,
        process_periods=[PERIOD],
    )

    units = pipelines[0].get_process_units()
    problem = simulation.process_problems[0]
    configs = simulation.process_configurations[problem.process_pipeline_id]

    # -- Configure units --
    shaft = next(h for h in problem.configuration_handlers if isinstance(h, Shaft))
    shaft.set_speed(10000)

    for unit_id, config in configs.items():
        unit = next(u for u in units if u.get_id() == unit_id)
        match config:
            case TimeSeriesTemperatureSetterConfiguration():
                unit.set_temperature(Unit.CELSIUS.to(Unit.KELVIN)(config.temperature_in_celsius.get_masked_values()[0]))
            case TimeSeriesSplitterConfiguration():
                unit.set_rate(config.offtake_rate.get_stream_day_values()[0])

    # -- Run pipeline --
    inlet_stream = fluid_service.create_stream_from_standard_rate(
        fluid_model=simulation.get_inlet_streams()[0].fluid_model,
        pressure_bara=20.0,
        temperature_kelvin=303.15,
        standard_rate_m3_per_day=2_000_000,
    )

    outlet = propagate_stream_many(units, inlet_stream)

    # -- Assert: mass is conserved — outlet = inlet - offtake --
    offtake_rate_sm3_per_day = yaml_splitter.offtake_rate.value
    expected_offtake_mass_rate = fluid_service.standard_rate_to_mass_rate(
        fluid_model=simulation.get_inlet_streams()[0].fluid_model,
        standard_rate_m3_per_day=offtake_rate_sm3_per_day,
    )

    assert outlet.mass_rate_kg_per_h == pytest.approx(
        inlet_stream.mass_rate_kg_per_h - expected_offtake_mass_rate,
        rel=1e-10,
    )
