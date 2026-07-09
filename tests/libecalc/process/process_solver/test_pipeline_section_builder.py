from uuid import uuid4

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.process.process_pipeline.process_pipeline import ProcessPipeline, ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.pipeline_section_builder import (
    build_pipeline_sections,
)
from libecalc.process.process_solver.pipeline_section_build_input import (
    AntiSurgeInput,
    PipelineSectionBuildConstraint,
    PipelineSectionBuildProblem,
    PipelineSectionBuildProblemSection,
    PressureControlInput,
)
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType
from libecalc.process.process_solver.section_assembly import AssembledSection, assemble_process_section
from libecalc.process.shaft import VariableSpeedShaft


def _constraint(
    pressure_control: PressureControlType,
    anti_surge: AntiSurgeType,
) -> PipelineSectionBuildConstraint:
    return PipelineSectionBuildConstraint(
        pressure_control=PressureControlInput(type=pressure_control),
        anti_surge=AntiSurgeInput(type=anti_surge),
    )


def _process_problem_section(assembled_process_section: AssembledSection) -> PipelineSectionBuildProblemSection:
    return PipelineSectionBuildProblemSection(
        process_unit_ids=[unit.get_id() for unit in assembled_process_section.process_units],
        configuration_handlers=assembled_process_section.configuration_handlers,
        constraint=_constraint(
            pressure_control="INDIVIDUAL_ASV_RATE",
            anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
        ),
    )


def test_prepares_two_sections_from_one_pipeline(
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
    lp_assembled_process_section = assemble_process_section(
        process_units=lp_units_raw,
        anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
        pressure_control="INDIVIDUAL_ASV_RATE",
        fluid_service=fluid_service,
    )
    hp_assembled_process_section = assemble_process_section(
        process_units=hp_units_raw,
        anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
        pressure_control="INDIVIDUAL_ASV_RATE",
        fluid_service=fluid_service,
    )

    # Store both assembled sections in one physical process pipeline.
    process_pipeline = ProcessPipeline(
        name="two-section-pipeline",
        stream_propagators=[
            *lp_assembled_process_section.process_units,
            *hp_assembled_process_section.process_units,
        ],
    )

    # Define the section boundaries as ProcessProblemSections.
    lp_process_problem_section = _process_problem_section(lp_assembled_process_section)
    hp_process_problem_section = _process_problem_section(hp_assembled_process_section)

    process_problem = PipelineSectionBuildProblem(
        process_problem_sections=[lp_process_problem_section, hp_process_problem_section],
        configuration_handlers=[shaft],
        process_pipeline_id=process_pipeline.get_id(),
    )

    # Prepare sections for the shared-shaft MultiPressureSolver.
    pipeline_sections = build_pipeline_sections(
        process_pipeline=process_pipeline,
        process_problem=process_problem,
        root_finding_strategy=root_finding_strategy,
    )

    assert len(pipeline_sections) == 2
    assert pipeline_sections[0].process_pipeline_id == process_pipeline.get_id()
    assert pipeline_sections[1].process_pipeline_id == process_pipeline.get_id()
    assert pipeline_sections[0].shaft_id == shaft.get_id()
    assert pipeline_sections[1].shaft_id == shaft.get_id()


def test_prepare_pipeline_sections_raises_when_section_references_unit_missing_from_pipeline():
    section = PipelineSectionBuildProblemSection(
        process_unit_ids=[ProcessUnitId(uuid4())],
        configuration_handlers=[],
        constraint=_constraint(
            pressure_control="INDIVIDUAL_ASV_RATE",
            anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
        ),
    )

    process_problem = PipelineSectionBuildProblem(
        process_problem_sections=[section],
        configuration_handlers=[],
        process_pipeline_id=ProcessPipelineId(uuid4()),
    )
    process_pipeline = ProcessPipeline(
        name="empty-pipeline",
        stream_propagators=[],
        process_pipeline_id=process_problem.process_pipeline_id,
    )

    with pytest.raises(EcalcValidationException, match="Process section references units not found in pipeline"):
        build_pipeline_sections(
            process_pipeline=process_pipeline,
            process_problem=process_problem,
        )
