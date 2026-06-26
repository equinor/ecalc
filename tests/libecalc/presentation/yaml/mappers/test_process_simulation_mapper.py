from datetime import datetime

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.time_utils import Period
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.inlet import Inlet
from libecalc.process.process_units.liquid_remover import LiquidRemover
from libecalc.process.process_units.outlet import Outlet
from libecalc.process.process_units.pressure_dropper import PressureDropper
from libecalc.process.process_units.temperature_setter import TemperatureSetter
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompressorBuilder,
    YamlLiquidRemoverBuilder,
    YamlMixerBuilder,
    YamlPressureDropperBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    YamlSplitterBuilder,
    YamlTemperatureSetterBuilder,
)

PERIOD = Period(start=datetime(2020, 1, 1), end=datetime(2030, 1, 1))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_pipeline(name: str = "train_1"):
    return (
        YamlProcessPipelineBuilder()
        .with_name(name)
        .with_item(target=YamlPressureDropperBuilder().with_test_data().validate())
        .with_item(target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .with_item(target=YamlLiquidRemoverBuilder().with_test_data().validate())
        .with_item(target=YamlCompressorBuilder().with_test_data().validate())
        .validate()
    )


def _build_simulation_with_pipeline(
    pipeline,
    name: str = "test_sim",
    pressure_control: PressureControlType = "DOWNSTREAM_CHOKE",
    outlet_pressure: float = 100.0,
):
    """Build a YamlProcessSimulation with one pipeline and default stream distribution."""
    return (
        YamlProcessSimulationBuilder()
        .with_name(name)
        .with_pipeline(
            pipeline,
            pressure_control=pressure_control,
            outlet_pressure=outlet_pressure,
        )
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )


# ---------------------------------------------------------------------------
# Tests: basic structure
# ---------------------------------------------------------------------------


def test_mapper_returns_one_pipeline_per_target(process_simulation_mapper):
    """One ProcessPipeline is produced per YAML target."""
    yaml_simulation = (
        YamlProcessSimulationBuilder()
        .with_name("multi")
        .with_pipeline(_simple_pipeline("train_a"))
        .with_pipeline(_simple_pipeline("train_b"))
        .with_stream_distribution(
            YamlCommonStreamDistributionBuilder().with_test_data().with_rate_fractions([0.5, 0.5]).validate()
        )
        .validate()
    )

    pipelines, _ = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_simulation,
        process_periods=[PERIOD],
    )

    assert len(pipelines) == 2
    assert {p.get_name() for p in pipelines} == {"train_a", "train_b"}


# ---------------------------------------------------------------------------
# Tests: pipeline composition (mapper adds infrastructure units)
# ---------------------------------------------------------------------------


def test_mapper_wraps_compressor_segment_with_mixer_and_splitter(process_simulation_mapper):
    """Each compressor segment is wrapped with DirectMixer + DirectSplitter to enable
    ASV recirculation. This is not visible in YAML but added by the mapper."""
    yaml_simulation = _build_simulation_with_pipeline(_simple_pipeline())

    pipelines, _ = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_simulation,
        process_periods=[PERIOD],
    )

    units = pipelines[0].get_process_units()
    assert isinstance(units[0], Inlet)
    assert isinstance(units[1], DirectMixer)
    assert isinstance(units[-1], Outlet)
    splitter_index = next(i for i, u in enumerate(units) if isinstance(u, DirectSplitter))
    compressor_index = next(i for i, u in enumerate(units) if isinstance(u, Compressor))
    assert splitter_index > compressor_index


def test_mapper_preserves_yaml_unit_order_inside_segment(process_simulation_mapper):
    """User-defined units appear in the order specified in YAML."""
    yaml_simulation = _build_simulation_with_pipeline(_simple_pipeline())

    pipelines, _ = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_simulation,
        process_periods=[PERIOD],
    )

    units = pipelines[0].get_process_units()

    def position_of(unit_type):
        return next(i for i, u in enumerate(units) if isinstance(u, unit_type))

    # YAML order: PressureDropper → TemperatureSetter → LiquidRemover → Compressor
    assert position_of(PressureDropper) < position_of(TemperatureSetter)
    assert position_of(TemperatureSetter) < position_of(LiquidRemover)
    assert position_of(LiquidRemover) < position_of(Compressor)


def test_mapper_adds_choke_for_downstream_choke_pressure_control(process_simulation_mapper):
    """DOWNSTREAM_CHOKE pressure control adds a Choke at the end of the pipeline."""
    yaml_simulation = _build_simulation_with_pipeline(_simple_pipeline(), pressure_control="DOWNSTREAM_CHOKE")

    pipelines, _ = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_simulation,
        process_periods=[PERIOD],
    )

    units = pipelines[0].get_process_units()
    assert isinstance(units[0], Inlet)
    assert isinstance(units[-2], Choke)
    assert isinstance(units[-1], Outlet)


def test_mapper_adds_choke_for_upstream_choke_pressure_control(process_simulation_mapper):
    """UPSTREAM_CHOKE pressure control adds a Choke at the very start of the pipeline."""
    yaml_simulation = _build_simulation_with_pipeline(_simple_pipeline(), pressure_control="UPSTREAM_CHOKE")

    pipelines, _ = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_simulation,
        process_periods=[PERIOD],
    )

    units = pipelines[0].get_process_units()
    assert isinstance(units[0], Inlet)
    assert isinstance(units[1], Choke)
    assert isinstance(units[-1], Outlet)


def test_mixer_and_splitter_are_placed_between_asv_loops(process_simulation_mapper):
    """Mixer and Splitter must sit between ASV recirculation loops, not inside one."""
    yaml_pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train_with_mixer_and_splitter")
        .with_item(name="temp_setter_1", target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .with_item(name="compressor_1", target=YamlCompressorBuilder().with_test_data().validate())
        .with_item(target=YamlSplitterBuilder().with_test_data().validate())
        .with_item(target=YamlMixerBuilder().with_test_data().validate())
        .with_item(name="temp_setter_2", target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .with_item(name="compressor_2", target=YamlCompressorBuilder().with_test_data().validate())
        .validate()
    )
    yaml_simulation = _build_simulation_with_pipeline(yaml_pipeline, pressure_control="INDIVIDUAL_ASV_RATE")

    pipelines, _ = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_simulation,
        process_periods=[PERIOD],
    )

    units = pipelines[0].get_process_units()
    unit_types = [type(u).__name__ for u in units]

    assert unit_types == [
        "Inlet",
        "DirectMixer",
        "TemperatureSetter",
        "Compressor",
        "DirectSplitter",  # ASV loop 1
        "Splitter",  # between loops
        "Mixer",  # between loops
        "DirectMixer",
        "TemperatureSetter",
        "Compressor",
        "DirectSplitter",  # ASV loop 2
        "Outlet",
    ]


# ---------------------------------------------------------------------------
# Tests: strategy mapping
# ---------------------------------------------------------------------------


def test_incompatible_strategies_raises_validation_exception(process_simulation_mapper):
    """Test that incompatible ANTI_SURGE and PRESSURE_CONTROL strategies raise exception."""
    mapper = process_simulation_mapper

    yaml_simulation = YamlProcessSimulationBuilder().with_test_data().validate()

    # Use incompatible combinations
    pipeline = yaml_simulation.targets[0].target

    constraint = yaml_simulation.constraints[pipeline.name][0]
    constraint.anti_surge = "INDIVIDUAL_ASV"
    constraint.pressure_control = "COMMON_ASV"

    # Check that validation fails
    with pytest.raises(EcalcValidationException) as exc_info:
        mapper.map_process_simulation(yaml_simulation, process_periods=[PERIOD])

    assert "PRESSURE_CONTROL 'COMMON_ASV' requires ANTI_SURGE 'COMMON_ASV', got 'INDIVIDUAL_ASV'" in str(exc_info.value)


def test_incompatible_common_asv_with_individual_asv_rate(process_simulation_mapper):
    """Test that COMMON_ASV anti-surge + INDIVIDUAL_ASV_RATE pressure control raises exception."""
    mapper = process_simulation_mapper

    yaml_simulation = YamlProcessSimulationBuilder().with_test_data().validate()

    pipeline = yaml_simulation.targets[0].target

    constraint = yaml_simulation.constraints[pipeline.name][0]
    constraint.anti_surge = "COMMON_ASV"
    constraint.pressure_control = "INDIVIDUAL_ASV_RATE"

    with pytest.raises(EcalcValidationException):
        mapper.map_process_simulation(yaml_simulation, process_periods=[PERIOD])


def test_incompatible_common_asv_with_individual_asv_pressure(process_simulation_mapper):
    """Test that COMMON_ASV anti-surge + INDIVIDUAL_ASV_PRESSURE pressure control raises exception."""
    mapper = process_simulation_mapper

    yaml_simulation = YamlProcessSimulationBuilder().with_test_data().validate()

    pipeline = yaml_simulation.targets[0].target

    constraint = yaml_simulation.constraints[pipeline.name][0]
    constraint.anti_surge = "COMMON_ASV"
    constraint.pressure_control = "INDIVIDUAL_ASV_PRESSURE"

    with pytest.raises(EcalcValidationException):
        mapper.map_process_simulation(yaml_simulation, process_periods=[PERIOD])


def test_compatible_strategies_succeeds(process_simulation_mapper):
    """Test that compatible strategies pass validation."""
    mapper = process_simulation_mapper

    yaml_simulation = YamlProcessSimulationBuilder().with_test_data().validate()

    # Use compatible combinations
    pipeline = yaml_simulation.targets[0].target

    constraint = yaml_simulation.constraints[pipeline.name][0]
    constraint.anti_surge = "INDIVIDUAL_ASV"
    constraint.pressure_control = "INDIVIDUAL_ASV_PRESSURE"

    # Run without exception
    mapper.map_process_simulation(yaml_simulation, process_periods=[PERIOD])


# ---------------------------------------------------------------------------
# Tests: trailing units
# ---------------------------------------------------------------------------


def test_mapper_places_trailing_units_after_last_asv_loop(process_simulation_mapper):
    """Units after the last compressor are placed outside any ASV recirculation loop."""
    yaml_pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train_with_aftercooler")
        .with_item(name="temp_setter_1", target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .with_item(name="compressor_1", target=YamlCompressorBuilder().with_test_data().validate())
        .with_item(name="temp_setter_2", target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .with_item(name="compressor_2", target=YamlCompressorBuilder().with_test_data().validate())
        .with_item(name="temp_setter_3", target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .validate()
    )
    yaml_simulation = _build_simulation_with_pipeline(yaml_pipeline, pressure_control="INDIVIDUAL_ASV_RATE")

    pipelines, _ = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_simulation,
        process_periods=[PERIOD],
    )

    units = pipelines[0].get_process_units()

    # Two ASV loops = two DirectSplitters. Trailing TemperatureSetter should be after both.
    splitter_indices = [i for i, u in enumerate(units) if isinstance(u, DirectSplitter)]
    assert len(splitter_indices) == 2

    trailing_temp_index = len(units) - 2
    assert isinstance(units[trailing_temp_index], TemperatureSetter)
    assert trailing_temp_index > max(splitter_indices)


# ---------------------------------------------------------------------------
# Tests: process units
# ---------------------------------------------------------------------------


def test_duplicate_process_unit_names_not_allowed(process_simulation_mapper):
    """Duplicate process unit names are not allowed within a process."""
    yaml_pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train_with_duplicate_unit_names")
        .with_item(name="temp_setter_1", target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .with_item(name="compressor_1", target=YamlCompressorBuilder().with_test_data().validate())
        .with_item(name="temp_setter_1", target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .with_item(name="compressor_2", target=YamlCompressorBuilder().with_test_data().validate())
        .validate()
    )
    yaml_simulation = _build_simulation_with_pipeline(yaml_pipeline, pressure_control="INDIVIDUAL_ASV_RATE")

    with pytest.raises(EcalcValidationException) as exc_info:
        process_simulation_mapper.map_process_simulation(yaml_simulation, process_periods=[PERIOD])

    assert "Duplicate process unit name 'temp_setter_1'" in str(exc_info.value)
