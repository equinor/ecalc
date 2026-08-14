from datetime import datetime

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.time_utils import Period
from libecalc.ecalc_model.process_simulation import Constraint
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlProcessConstraint
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
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
from libecalc.process.shaft import VariableSpeedShaft
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
    """Build a YamlProcessSimulation with one pipeline and default stream distribution.
    Returns (simulation, pipeline_references) tuple."""
    builder = (
        YamlProcessSimulationBuilder()
        .with_name(name)
        .with_pipeline(
            pipeline,
            pressure_control=pressure_control,
            outlet_pressure=outlet_pressure,
        )
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
    )
    return builder.validate(), builder.get_pipeline_references()


# ---------------------------------------------------------------------------
# Tests: basic structure
# ---------------------------------------------------------------------------


def test_mapper_returns_one_pipeline_per_target(process_simulation_mapper_factory):
    """One ProcessPipeline is produced per YAML target."""
    builder = (
        YamlProcessSimulationBuilder()
        .with_name("multi")
        .with_pipeline(_simple_pipeline("train_a"))
        .with_pipeline(_simple_pipeline("train_b"))
        .with_stream_distribution(
            YamlCommonStreamDistributionBuilder().with_test_data().with_rate_fractions([0.5, 0.5]).validate()
        )
    )
    yaml_simulation = builder.validate()

    pipelines, _ = process_simulation_mapper_factory(builder.get_pipeline_references()).map_process_simulation(
        yaml_process_simulation=yaml_simulation,
    )

    assert len(pipelines) == 2
    assert {p.get_name() for p in pipelines} == {"train_a", "train_b"}


# ---------------------------------------------------------------------------
# Tests: pipeline composition (mapper adds infrastructure units)
# ---------------------------------------------------------------------------


def test_mapper_wraps_compressor_segment_with_mixer_and_splitter(process_simulation_mapper_factory):
    """Each compressor segment is wrapped with DirectMixer + DirectSplitter to enable
    ASV recirculation. This is not visible in YAML but added by the mapper."""
    yaml_simulation, refs = _build_simulation_with_pipeline(_simple_pipeline())

    pipelines, _ = process_simulation_mapper_factory(refs).map_process_simulation(
        yaml_process_simulation=yaml_simulation,
    )

    units = pipelines[0].get_process_units()
    assert isinstance(units[0], Inlet)
    assert isinstance(units[1], DirectMixer)
    assert isinstance(units[-1], Outlet)
    splitter_index = next(i for i, u in enumerate(units) if isinstance(u, DirectSplitter))
    compressor_index = next(i for i, u in enumerate(units) if isinstance(u, Compressor))
    assert splitter_index > compressor_index


def test_mapper_preserves_yaml_unit_order_inside_segment(process_simulation_mapper_factory):
    """User-defined units appear in the order specified in YAML."""
    yaml_simulation, refs = _build_simulation_with_pipeline(_simple_pipeline())

    pipelines, _ = process_simulation_mapper_factory(refs).map_process_simulation(
        yaml_process_simulation=yaml_simulation,
    )

    units = pipelines[0].get_process_units()

    def position_of(unit_type):
        return next(i for i, u in enumerate(units) if isinstance(u, unit_type))

    # YAML order: PressureDropper → TemperatureSetter → LiquidRemover → Compressor
    assert position_of(PressureDropper) < position_of(TemperatureSetter)
    assert position_of(TemperatureSetter) < position_of(LiquidRemover)
    assert position_of(LiquidRemover) < position_of(Compressor)


def test_mapper_adds_choke_for_downstream_choke_pressure_control(process_simulation_mapper_factory):
    """DOWNSTREAM_CHOKE pressure control adds a Choke at the end of the pipeline."""
    yaml_simulation, refs = _build_simulation_with_pipeline(_simple_pipeline(), pressure_control="DOWNSTREAM_CHOKE")

    pipelines, _ = process_simulation_mapper_factory(refs).map_process_simulation(
        yaml_process_simulation=yaml_simulation,
    )

    units = pipelines[0].get_process_units()
    assert isinstance(units[0], Inlet)
    assert isinstance(units[-2], Choke)
    assert isinstance(units[-1], Outlet)


def test_mapper_adds_choke_for_upstream_choke_pressure_control(process_simulation_mapper_factory):
    """UPSTREAM_CHOKE pressure control adds a Choke at the very start of the pipeline."""
    yaml_simulation, refs = _build_simulation_with_pipeline(_simple_pipeline(), pressure_control="UPSTREAM_CHOKE")

    pipelines, _ = process_simulation_mapper_factory(refs).map_process_simulation(
        yaml_process_simulation=yaml_simulation,
    )

    units = pipelines[0].get_process_units()
    assert isinstance(units[0], Inlet)
    assert isinstance(units[1], Choke)
    assert isinstance(units[-1], Outlet)


def test_mixer_and_splitter_are_placed_between_asv_loops(process_simulation_mapper_factory):
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
    yaml_simulation, refs = _build_simulation_with_pipeline(yaml_pipeline, pressure_control="INDIVIDUAL_ASV_RATE")

    pipelines, _ = process_simulation_mapper_factory(refs).map_process_simulation(
        yaml_process_simulation=yaml_simulation,
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


def test_incompatible_strategies_raises_validation_exception(process_simulation_mapper_factory):
    """Test that incompatible ANTI_SURGE and PRESSURE_CONTROL strategies raise exception."""
    builder = YamlProcessSimulationBuilder().with_test_data()
    yaml_simulation = builder.validate()

    # Use incompatible combinations
    pipeline_name = yaml_simulation.targets[0]

    constraint = yaml_simulation.constraints[pipeline_name][0]
    constraint.anti_surge = "INDIVIDUAL_ASV"
    constraint.pressure_control = "COMMON_ASV"

    # Check that validation fails
    mapper = process_simulation_mapper_factory(builder.get_pipeline_references())
    with pytest.raises(EcalcValidationException) as exc_info:
        mapper.map_process_simulation(yaml_simulation)

    assert "PRESSURE_CONTROL 'COMMON_ASV' requires ANTI_SURGE 'COMMON_ASV', got 'INDIVIDUAL_ASV'" in str(exc_info.value)


def test_incompatible_common_asv_with_individual_asv_rate(process_simulation_mapper_factory):
    """Test that COMMON_ASV anti-surge + INDIVIDUAL_ASV_RATE pressure control raises exception."""
    builder = YamlProcessSimulationBuilder().with_test_data()
    yaml_simulation = builder.validate()

    pipeline_name = yaml_simulation.targets[0]

    constraint = yaml_simulation.constraints[pipeline_name][0]
    constraint.anti_surge = "COMMON_ASV"
    constraint.pressure_control = "INDIVIDUAL_ASV_RATE"

    mapper = process_simulation_mapper_factory(builder.get_pipeline_references())
    with pytest.raises(EcalcValidationException):
        mapper.map_process_simulation(yaml_simulation)


def test_incompatible_common_asv_with_individual_asv_pressure(process_simulation_mapper_factory):
    """Test that COMMON_ASV anti-surge + INDIVIDUAL_ASV_PRESSURE pressure control raises exception."""
    builder = YamlProcessSimulationBuilder().with_test_data()
    yaml_simulation = builder.validate()

    pipeline_name = yaml_simulation.targets[0]

    constraint = yaml_simulation.constraints[pipeline_name][0]
    constraint.anti_surge = "COMMON_ASV"
    constraint.pressure_control = "INDIVIDUAL_ASV_PRESSURE"

    mapper = process_simulation_mapper_factory(builder.get_pipeline_references())
    with pytest.raises(EcalcValidationException):
        mapper.map_process_simulation(yaml_simulation)


def test_compatible_strategies_succeeds(process_simulation_mapper_factory):
    """Test that compatible strategies pass validation."""
    builder = YamlProcessSimulationBuilder().with_test_data()
    yaml_simulation = builder.validate()

    # Use compatible combinations
    pipeline_name = yaml_simulation.targets[0]

    constraint = yaml_simulation.constraints[pipeline_name][0]
    constraint.anti_surge = "INDIVIDUAL_ASV"
    constraint.pressure_control = "INDIVIDUAL_ASV_PRESSURE"

    # Run without exception
    mapper = process_simulation_mapper_factory(builder.get_pipeline_references())
    mapper.map_process_simulation(yaml_simulation)


# ---------------------------------------------------------------------------
# Tests: trailing units
# ---------------------------------------------------------------------------


def test_mapper_places_trailing_units_after_last_asv_loop(process_simulation_mapper_factory):
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
    yaml_simulation, refs = _build_simulation_with_pipeline(yaml_pipeline, pressure_control="INDIVIDUAL_ASV_RATE")

    pipelines, _ = process_simulation_mapper_factory(refs).map_process_simulation(
        yaml_process_simulation=yaml_simulation,
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


def test_duplicate_process_unit_names_not_allowed(process_simulation_mapper_factory):
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
    yaml_simulation, refs = _build_simulation_with_pipeline(yaml_pipeline, pressure_control="INDIVIDUAL_ASV_RATE")

    with pytest.raises(EcalcValidationException) as exc_info:
        process_simulation_mapper_factory(refs).map_process_simulation(yaml_simulation)

    assert "Duplicate process unit name 'temp_setter_1'" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Tests: process sections
# ---------------------------------------------------------------------------


def test_mapper_builds_single_process_problem_section(process_simulation_mapper_factory):
    """A single constraint pipeline produces one ProcessProblemSection."""
    yaml_simulation, refs = _build_simulation_with_pipeline(_simple_pipeline())
    _, simulation = process_simulation_mapper_factory(refs).map_process_simulation(
        yaml_process_simulation=yaml_simulation,
    )
    assert len(simulation.process_problems) == 1
    problem = simulation.process_problems[0]

    assert len(problem.get_configuration_handlers()) == 3
    assert isinstance(problem.get_configuration_handlers()[0], VariableSpeedShaft)

    assert len(problem.get_process_problem_sections()) == 1

    section = problem.get_process_problem_sections()[0]

    assert isinstance(section.get_constraint(), Constraint)

    # Section-specific solver handlers (ASV-loop, chokes etc.) live on the section.
    # assert any(isinstance(h, RecirculationLoop) for h in section.configuration_handlers)


def test_mapper_builds_multiple_process_problem_sections(process_simulation_mapper_factory):
    """Each mapped process section becomes a ProcessProblemSection"""
    yaml_pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train_with_intermediate_constraint")
        .with_item(name="temp_setter_1", target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .with_item(name="compressor_1", target=YamlCompressorBuilder().with_test_data().validate())
        .with_item(target=YamlMixerBuilder().with_test_data().validate())
        .with_item(name="temp_setter_2", target=YamlTemperatureSetterBuilder().with_test_data().validate())
        .with_item(name="compressor_2", target=YamlCompressorBuilder().with_test_data().validate())
        .validate()
    )

    yaml_simulation, refs = _build_simulation_with_pipeline(pipeline=yaml_pipeline, pressure_control="DOWNSTREAM_CHOKE")

    constraint = YamlProcessConstraint(
        process_unit="compressor_1",
        outlet_pressure=30,
        pressure_control="INDIVIDUAL_ASV_RATE",
        anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
    )
    yaml_simulation.constraints[yaml_pipeline.name].insert(0, constraint)

    _, simulation = process_simulation_mapper_factory(refs).map_process_simulation(
        yaml_process_simulation=yaml_simulation,
    )

    problem = simulation.process_problems[0]

    # Train-wide handlers (currently only Shaft) remain on ProcessProblem.
    assert len(problem.get_configuration_handlers()) == 4
    assert isinstance(problem.get_configuration_handlers()[0], VariableSpeedShaft)

    # Each solver section owns its own constraint and section-specific handlers.
    assert len(problem.get_process_problem_sections()) == 2

    assert problem.get_process_problem_sections()[0].get_pressure_control().type == "INDIVIDUAL_ASV_RATE"
    assert problem.get_process_problem_sections()[1].get_pressure_control().type == "DOWNSTREAM_CHOKE"

    # assert any(isinstance(h, RecirculationLoop) for h in problem.get_process_problem_sections()[0].configuration_handlers)
    # assert any(
    #    isinstance(h, ChokeConfigurationHandler) for h in problem.get_process_problem_sections()[1].configuration_handlers
    # )

    assert (
        problem.get_process_problem_sections()[0].get_constraint().target_process_unit_id
        != problem.get_process_problem_sections()[1].get_constraint().target_process_unit_id
    )
