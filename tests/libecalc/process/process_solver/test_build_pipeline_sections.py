from uuid import uuid4

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.process.process_pipeline.process_pipeline import (
    ProcessPipeline,
    ProcessPipelineId,
    ProcessPipelineSection,
    ProcessPipelineSectionId,
)
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.build_pipeline_sections import (
    build_pipeline_sections,
)
from libecalc.process.process_solver.build_pipeline_sections_input import (
    BuildPipelineSectionsInput,
    BuildPipelineSectionInput,
)
from libecalc.process.process_solver.pressure_control.individual_asv import IndividualASVRateControlStrategy
from libecalc.process.process_solver.process_pipeline_runner import ProcessPipelineRunner
from libecalc.process.process_solver.section_assembly import assemble_process_section
from libecalc.process.shaft import VariableSpeedShaft


def _build_section_input(process_pipeline_section: ProcessPipelineSection) -> BuildPipelineSectionInput:
    return BuildPipelineSectionInput(
        process_pipeline_section_id=process_pipeline_section.get_id(),
        pressure_control="INDIVIDUAL_ASV_RATE",
        anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
    )


def test_build_pipeline_sections_builds_two_sections_from_one_pipeline(
    stream_factory,
    chart_data_factory,
    compressor_factory,
    stage_units_factory,
    variable_speed_chart_data_factory,
    fluid_service,
    root_finding_strategy,
):
    temperature = 300.0
    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0,
        pressure_bara=30.0,
        temperature_kelvin=temperature,
    )
    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)

    # Build two raw compressor sections sharing one shaft.
    shaft = VariableSpeedShaft()
    lp_chart_data = variable_speed_chart_data_factory(
        chart_data_factory,
        min_rate=0.0,
        max_rate=q0 * 10.0,
        head_hi=150_000.0,
        head_lo=50_000.0,
        eff=0.75,
    )
    hp_chart_data = variable_speed_chart_data_factory(
        chart_data_factory,
        min_rate=0.0,
        max_rate=q0 * 10.0,
        head_hi=120_000.0,
        head_lo=30_000.0,
        eff=0.72,
    )

    lp_compressor = compressor_factory(chart_data=lp_chart_data)
    hp_compressor = compressor_factory(chart_data=hp_chart_data)

    lp_units_raw = stage_units_factory(compressor=lp_compressor, shaft=shaft, temperature_kelvin=temperature)
    hp_units_raw = stage_units_factory(compressor=hp_compressor, shaft=shaft, temperature_kelvin=temperature)

    # Add solver topology for each section: ASV loops and section handlers.
    lp_assembled_section = assemble_process_section(
        process_units=lp_units_raw,
        anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
        pressure_control="INDIVIDUAL_ASV_RATE",
        fluid_service=fluid_service,
    )
    hp_assembled_section = assemble_process_section(
        process_units=hp_units_raw,
        anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
        pressure_control="INDIVIDUAL_ASV_RATE",
        fluid_service=fluid_service,
    )

    # Store both assembled sections in one physical process pipeline.
    lp_pipeline_section = ProcessPipelineSection(process_units=lp_assembled_section.process_units)
    hp_pipeline_section = ProcessPipelineSection(process_units=hp_assembled_section.process_units)

    process_pipeline = ProcessPipeline(
        name="two-section-pipeline",
        process_pipeline_sections=[lp_pipeline_section, hp_pipeline_section],
    )

    # Build input for section
    lp_build_section_input = _build_section_input(lp_pipeline_section)
    hp_build_section_input = _build_section_input(hp_pipeline_section)

    build_input = BuildPipelineSectionsInput(
        sections=[lp_build_section_input, hp_build_section_input],
        configuration_handlers=[
            shaft,
            *lp_assembled_section.configuration_handlers,
            *hp_assembled_section.configuration_handlers,
        ],
        process_pipeline_id=process_pipeline.get_id(),
    )

    pipeline_sections = build_pipeline_sections(
        process_pipeline=process_pipeline,
        build_input=build_input,
        root_finding_strategy=root_finding_strategy,
    )

    assert len(pipeline_sections) == 2
    assert pipeline_sections[0].process_pipeline_section_id == lp_pipeline_section.get_id()
    assert pipeline_sections[1].process_pipeline_section_id == hp_pipeline_section.get_id()

    for pipeline_section in pipeline_sections:
        assert pipeline_section.process_pipeline_id == process_pipeline.get_id()
        assert pipeline_section.shaft_id == shaft.get_id()
        assert pipeline_section.root_finding_strategy is root_finding_strategy
        assert isinstance(pipeline_section.runner, ProcessPipelineRunner)
        assert isinstance(pipeline_section.anti_surge_strategy, IndividualASVAntiSurgeStrategy)
        assert isinstance(pipeline_section.pressure_control_strategy, IndividualASVRateControlStrategy)


def test_build_pipeline_sections_raises_when_section_references_pipeline_section_missing_from_pipeline():
    section = BuildPipelineSectionInput(
        process_pipeline_section_id=ProcessPipelineSectionId(uuid4()),
        pressure_control="INDIVIDUAL_ASV_RATE",
        anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
    )

    build_input = BuildPipelineSectionsInput(
        sections=[section],
        configuration_handlers=[],
        process_pipeline_id=ProcessPipelineId(uuid4()),
    )
    process_pipeline = ProcessPipeline(
        name="empty-pipeline",
        process_pipeline_sections=[],
        process_pipeline_id=build_input.process_pipeline_id,
    )

    with pytest.raises(EcalcValidationException, match="pipeline section not found"):
        build_pipeline_sections(
            process_pipeline=process_pipeline,
            build_input=build_input,
        )
