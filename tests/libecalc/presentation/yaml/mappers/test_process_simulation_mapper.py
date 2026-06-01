from datetime import datetime

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.time_utils import Period
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.liquid_remover import LiquidRemover
from libecalc.process.process_units.pressure_dropper import PressureDropper
from libecalc.process.process_units.temperature_setter import TemperatureSetter
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompressorBuilder,
    YamlLiquidRemoverBuilder,
    YamlPressureDropperBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
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
        .with_items(
            [
                YamlPressureDropperBuilder().with_test_data().validate(),
                YamlTemperatureSetterBuilder().with_test_data().validate(),
                YamlLiquidRemoverBuilder().validate(),
                YamlCompressorBuilder().with_test_data().validate(),
            ]
        )
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
    assert isinstance(units[0], DirectMixer)
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
    assert isinstance(units[-1], Choke)


def test_mapper_adds_choke_for_upstream_choke_pressure_control(process_simulation_mapper):
    """UPSTREAM_CHOKE pressure control adds a Choke at the very start of the pipeline."""
    yaml_simulation = _build_simulation_with_pipeline(_simple_pipeline(), pressure_control="UPSTREAM_CHOKE")

    pipelines, _ = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_simulation,
        process_periods=[PERIOD],
    )

    units = pipelines[0].get_process_units()
    assert isinstance(units[0], Choke)


# ---------------------------------------------------------------------------
# Tests: process problem / strategy mapping
# ---------------------------------------------------------------------------


def test_mapper_attaches_anti_surge_config_to_process_problem(process_simulation_mapper):
    """Anti-surge strategy follows from pressure control choice."""
    yaml_common = _build_simulation_with_pipeline(_simple_pipeline("train_common"), pressure_control="COMMON_ASV")
    yaml_individual = _build_simulation_with_pipeline(
        _simple_pipeline("train_individual"), pressure_control="INDIVIDUAL_ASV_RATE"
    )

    _, sim_common = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_common,
        process_periods=[PERIOD],
    )
    _, sim_individual = process_simulation_mapper.map_process_simulation(
        yaml_process_simulation=yaml_individual,
        process_periods=[PERIOD],
    )

    assert sim_common.process_problems[0].get_anti_surge_strategy().type == "COMMON_ASV"
    assert sim_individual.process_problems[0].get_anti_surge_strategy().type == "INDIVIDUAL_ASV"


# ---------------------------------------------------------------------------
# Tests: validation
# ---------------------------------------------------------------------------


def test_mapper_raises_when_pipeline_has_units_after_last_compressor(process_simulation_mapper):
    """Trailing units (after the last compressor) are not allowed."""
    pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("invalid_train")
        .with_items(
            [
                YamlCompressorBuilder().with_test_data().validate(),
                YamlPressureDropperBuilder().with_test_data().validate(),  # trailing
            ]
        )
        .validate()
    )
    yaml_simulation = _build_simulation_with_pipeline(pipeline)

    with pytest.raises(EcalcValidationException, match="after the last compressor"):
        process_simulation_mapper.map_process_simulation(
            yaml_process_simulation=yaml_simulation,
            process_periods=[PERIOD],
        )
