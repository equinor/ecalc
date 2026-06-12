from datetime import datetime

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.time_utils import Period
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlProcessConstraint
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.liquid_remover import LiquidRemover
from libecalc.process.process_units.mixer import Mixer
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


def test_mixer_and_splitter_are_placed_between_asv_loops(process_simulation_mapper):
    """Mixer and Splitter must sit between ASV recirculation loops, not inside one."""
    yaml_pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train_with_mixer_and_splitter")
        .with_items(
            [
                YamlTemperatureSetterBuilder().with_test_data().validate(),
                YamlCompressorBuilder().with_test_data().validate(),
                YamlSplitterBuilder().with_test_data().validate(),
                YamlMixerBuilder().with_test_data().validate(),
                YamlTemperatureSetterBuilder().with_test_data().validate(),
                YamlCompressorBuilder().with_test_data().validate(),
            ]
        )
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
    ]


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
# Tests: trailing units
# ---------------------------------------------------------------------------


def test_mapper_places_trailing_units_after_last_asv_loop(process_simulation_mapper):
    """Units after the last compressor are placed outside any ASV recirculation loop."""
    yaml_pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train_with_aftercooler")
        .with_items(
            [
                YamlTemperatureSetterBuilder().with_test_data().validate(),
                YamlCompressorBuilder().with_test_data().validate(),
                YamlTemperatureSetterBuilder().with_test_data().validate(),
                YamlCompressorBuilder().with_test_data().validate(),
                YamlTemperatureSetterBuilder().with_test_data().validate(),  # trailing
            ]
        )
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

    trailing_temp_index = len(units) - 1
    assert isinstance(units[trailing_temp_index], TemperatureSetter)
    assert trailing_temp_index > max(splitter_indices)


# ---------------------------------------------------------------------------
# Tests: typed constraints
# ---------------------------------------------------------------------------


def test_multiple_constraints_resolve_to_correct_units(process_simulation_mapper):
    """
    Multi-stage train: inlet conditioning, two compressors with interstage
    mixer (gas injection) and splitter (fuel offtake), pressure targets at three points.

    --- Assemble pipeline ---

             ASV loop 1                                                               ASV loop 2
    ┌─────────────────────────────────────┐                                 ┌─────────────────────────────────────┐
    │ cooler → scrubber → lp_compr.       │     →    mixer    → splitter →  │ cooler → scrubber → hp_compr.       │
    └─────────────────────────────────────┘                                 └─────────────────────────────────────┘
                                          ↑               ↑                                                       ↑
                                  constraint 1      constraint 2                                              constraint 3
                                   (30 bara)         (28 bara)                                                 (180 bara)

    """

    # --- Build pipeline units ---
    yaml_compressor_1 = YamlCompressorBuilder().with_test_data().validate()
    yaml_compressor_1.name = "lp_compressor"

    yaml_mixer = YamlMixerBuilder().with_test_data().validate()
    yaml_mixer.name = "gas_injection"

    yaml_splitter = YamlSplitterBuilder().with_test_data().validate()
    yaml_splitter.name = "fuel_offtake"

    yaml_compressor_2 = YamlCompressorBuilder().with_test_data().validate()
    yaml_compressor_2.name = "hp_compressor"

    yaml_pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("export_train")
        .with_items(
            [
                YamlTemperatureSetterBuilder().with_test_data().validate(),  # inlet cooling
                YamlLiquidRemoverBuilder().with_test_data().validate(),  # inlet scrubbing
                yaml_compressor_1,  # LP compression
                yaml_mixer,  # injection gas enters
                yaml_splitter,  # fuel gas leaves
                YamlTemperatureSetterBuilder().with_test_data().validate(),  # interstage cooling
                YamlLiquidRemoverBuilder().with_test_data().validate(),  # interstage scrubbing
                yaml_compressor_2,  # HP compression
            ]
        )
        .validate()
    )

    # --- Constraints: pressure targets at three points ---
    # NOTE: Constraint on mixer is resolvable here (mapper test), but not yet
    # actionable by MultiPressureSolver until PRESSURE_CONTROL is defined
    # per constraint rather than per pipeline.
    yaml_process_sim = _build_simulation_with_pipeline(yaml_pipeline)
    yaml_process_sim.constraints = [
        YamlProcessConstraint(target="export_train", unit="lp_compressor", outlet_pressure=30.0),
        YamlProcessConstraint(target="export_train", unit="gas_injection", outlet_pressure=28.0),
        YamlProcessConstraint(target="export_train", outlet_pressure=180.0),
    ]

    # --- Map and verify ---
    pipelines, simulation = process_simulation_mapper.map_process_simulation(yaml_process_sim, [PERIOD])
    problem = simulation.process_problems[0]
    units = pipelines[0].get_process_units()

    compressor_ids = [u.get_id() for u in units if isinstance(u, Compressor)]
    mixer_ids = [u.get_id() for u in units if isinstance(u, Mixer)]

    assert len(problem.constraints) == 3

    # LP compressor outlet: 30 bara before injection gas enters
    assert problem.constraints[0].target_unit_id == compressor_ids[0]

    # Mixer outlet: 28 bara after injection gas is mixed in
    assert problem.constraints[1].target_unit_id == mixer_ids[0]

    # Pipeline outlet: 180 bara final discharge
    assert problem.constraints[2].target_unit_id is None


def test_constraint_with_unknown_unit_raises(process_simulation_mapper):
    """Constraint referencing a non-existent unit should raise validation error."""
    pipeline = YamlProcessPipelineBuilder().with_test_data().with_name("train_a").validate()
    process_sim = _build_simulation_with_pipeline(pipeline)
    process_sim.constraints = [
        YamlProcessConstraint(target="train_a", unit="nonexistent", outlet_pressure=50.0),
    ]

    with pytest.raises(EcalcValidationException, match="unknown unit"):
        process_simulation_mapper.map_process_simulation(process_sim, [PERIOD])


def test_constraint_with_unknown_pipeline_raises(process_simulation_mapper):
    """Constraint referencing a non-existent pipeline should raise validation error."""
    pipeline = YamlProcessPipelineBuilder().with_test_data().with_name("train_a").validate()
    process_sim = _build_simulation_with_pipeline(pipeline)
    process_sim.constraints = [
        YamlProcessConstraint(target="nonexistent", outlet_pressure=100.0),
    ]

    with pytest.raises(EcalcValidationException, match="unknown process system"):
        process_simulation_mapper.map_process_simulation(process_sim, [PERIOD])
