from datetime import datetime
from uuid import uuid4

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.ecalc_model.process_simulation import (
    AntiSurgeConfig,
    Constraint,
    PressureControlConfig,
    ProcessProblem,
    ProcessProblemSection,
)
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.process.process_pipeline.process_pipeline import ProcessPipeline, ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.multi_pressure_solver import MultiPressureSolver
from libecalc.process.process_solver.pipeline_section_assembly import (
    PreparedActivePipelineSection,
    PreparedPassivePipelineSection,
    prepare_pipeline_sections,
)
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType
from libecalc.process.process_solver.section_assembly import AssembledSection, assemble_process_section
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.shaft import VariableSpeedShaft

PERIOD = Period(start=datetime(2020, 1, 1), end=datetime(2030, 1, 1))


def _constraint(
    target_pressure: float,
    target_process_unit_id: ProcessUnitId,
    pressure_control: PressureControlType,
    anti_surge: AntiSurgeType,
    expression_evaluator: ExpressionEvaluator,
) -> Constraint:
    return Constraint(
        outlet_pressure=TimeSeriesExpression(
            expression=target_pressure,
            expression_evaluator=expression_evaluator,
        ),
        pressure_control=PressureControlConfig(type=pressure_control),
        anti_surge=AntiSurgeConfig(type=anti_surge),
        target_process_unit_id=target_process_unit_id,
    )


def _active_process_problem_section(
    assembled_process_section: AssembledSection,
    compressor: Compressor,
    target_pressure: float,
    expression_evaluator: ExpressionEvaluator,
) -> ProcessProblemSection:
    return ProcessProblemSection(
        process_unit_ids=[unit.get_id() for unit in assembled_process_section.process_units],
        configuration_handlers=assembled_process_section.configuration_handlers,
        constraint=_constraint(
            target_pressure=target_pressure,
            target_process_unit_id=compressor.get_id(),
            pressure_control="INDIVIDUAL_ASV_RATE",
            anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
            expression_evaluator=expression_evaluator,
        ),
    )


def _passive_process_problem_section(
    assembled_process_section: AssembledSection,
    target_process_unit_id: ProcessUnitId,
    target_pressure: float,
    expression_evaluator: ExpressionEvaluator,
) -> ProcessProblemSection:
    return ProcessProblemSection(
        process_unit_ids=[unit.get_id() for unit in assembled_process_section.process_units],
        configuration_handlers=assembled_process_section.configuration_handlers,
        constraint=_constraint(
            target_pressure=target_pressure,
            target_process_unit_id=target_process_unit_id,
            pressure_control="DOWNSTREAM_CHOKE",
            anti_surge=AntiSurgeType.NO_ASV,
            expression_evaluator=expression_evaluator,
        ),
    )


def test_prepares_two_active_sections_from_one_pipeline_and_solves_with_multi_pressure_solver(
    stream_factory,
    chart_data_factory,
    compressor_factory,
    stage_units_factory,
    variable_speed_chart_data_factory,
    fluid_service,
    root_finding_strategy,
    expression_evaluator_factory,
):
    expression_evaluator = expression_evaluator_factory.from_periods(periods=[PERIOD])

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

    # Partition, validate and assemble sections.
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
    lp_process_problem_section = _active_process_problem_section(
        lp_assembled_process_section, lp_compressor, 60.0, expression_evaluator
    )
    hp_process_problem_section = _active_process_problem_section(
        hp_assembled_process_section, hp_compressor, 120.0, expression_evaluator
    )

    process_problem = ProcessProblem(
        process_problem_sections=[lp_process_problem_section, hp_process_problem_section],
        configuration_handlers=[shaft],
        process_pipeline_id=process_pipeline.get_id(),
    )

    # Prepare active sections for the shared-shaft MultiPressureSolver.
    prepared_pipeline_sections = prepare_pipeline_sections(
        process_pipeline=process_pipeline,
        process_problem=process_problem,
        root_finding_strategy=root_finding_strategy,
    )
    # This scenario only has active sections, so all prepared sections can be passed to MultiPressureSolver.
    active_sections = [
        section for section in prepared_pipeline_sections if isinstance(section, PreparedActivePipelineSection)
    ]
    assert len(active_sections) == len(prepared_pipeline_sections)

    pipeline_sections = [s.pipeline_section for s in active_sections]
    pressure_targets = [s.get_pressure_target(PERIOD) for s in active_sections]

    assert [target.value for target in pressure_targets] == [60.0, 120.0]
    assert len(pipeline_sections) == 2
    assert pipeline_sections[0].process_pipeline_id == process_pipeline.get_id()
    assert pipeline_sections[1].process_pipeline_id == process_pipeline.get_id()
    assert pipeline_sections[0].shaft_id == shaft.get_id()
    assert pipeline_sections[1].shaft_id == shaft.get_id()

    # Use the runtime PipelineSections produced for the active sections in this scenario.
    solution = MultiPressureSolver(pipeline_sections).find_solution(
        pressure_targets=pressure_targets,
        inlet_stream=inlet_stream,
    )
    assert solution.success
    lp_outlet = pipeline_sections[0].runner.run(inlet_stream)
    hp_outlet = pipeline_sections[1].runner.run(lp_outlet)
    assert lp_outlet.pressure_bara == pytest.approx(60.0, rel=1e-3)
    assert hp_outlet.pressure_bara == pytest.approx(120.0, rel=1e-3)


def test_prepare_pipeline_sections_preserves_active_and_passive_sections_in_order(
    chart_data_factory,
    compressor_factory,
    stage_units_factory,
    variable_speed_chart_data_factory,
    temperature_setter_factory,
    fluid_service,
    expression_evaluator_factory,
):
    expression_evaluator = expression_evaluator_factory.from_periods(periods=[PERIOD])
    shaft = VariableSpeedShaft()

    compressor = compressor_factory(
        chart_data=variable_speed_chart_data_factory(
            chart_data_factory,
            min_rate=0.0,
            max_rate=10_000.0,
            head_hi=150_000.0,
            head_lo=50_000.0,
            eff=0.75,
        )
    )

    active_units_raw = stage_units_factory(compressor=compressor, shaft=shaft)
    active_section = assemble_process_section(
        process_units=active_units_raw,
        anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
        pressure_control="INDIVIDUAL_ASV_RATE",
        fluid_service=fluid_service,
    )

    temperature_setter = temperature_setter_factory(required_temperature_kelvin=300.0)
    passive_section = assemble_process_section(
        process_units=[temperature_setter],
        anti_surge=AntiSurgeType.NO_ASV,
        pressure_control="DOWNSTREAM_CHOKE",
        fluid_service=fluid_service,
    )

    process_pipeline = ProcessPipeline(
        name="active-passive-pipeline",
        stream_propagators=[
            *active_section.process_units,
            *passive_section.process_units,
        ],
    )

    process_problem = ProcessProblem(
        process_problem_sections=[
            _active_process_problem_section(active_section, compressor, 60.0, expression_evaluator),
            _passive_process_problem_section(passive_section, temperature_setter.get_id(), 55.0, expression_evaluator),
        ],
        configuration_handlers=[shaft],
        process_pipeline_id=process_pipeline.get_id(),
    )

    # Prepare keeps all process problem sections in order, including passive sections.
    prepared_sections = prepare_pipeline_sections(
        process_pipeline=process_pipeline,
        process_problem=process_problem,
    )

    # Active sections become runtime PipelineSections; passive sections are retained for later process-level solving.
    assert isinstance(prepared_sections[0], PreparedActivePipelineSection)
    assert isinstance(prepared_sections[1], PreparedPassivePipelineSection)
    assert [section.get_pressure_target(PERIOD).value for section in prepared_sections] == [60.0, 55.0]
    assert [unit.get_id() for unit in prepared_sections[1].process_units] == [
        unit.get_id() for unit in passive_section.process_units
    ]


def test_prepare_pipeline_sections_raises_when_section_references_unit_missing_from_pipeline(
    expression_evaluator_factory,
):
    expression_evaluator = expression_evaluator_factory.from_periods(periods=[PERIOD])

    section = ProcessProblemSection(
        process_unit_ids=[ProcessUnitId(uuid4())],
        configuration_handlers=[],
        constraint=_constraint(
            target_pressure=60.0,
            target_process_unit_id=ProcessUnitId(uuid4()),
            pressure_control="INDIVIDUAL_ASV_RATE",
            anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
            expression_evaluator=expression_evaluator,
        ),
    )

    process_problem = ProcessProblem(
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
        prepare_pipeline_sections(
            process_pipeline=process_pipeline,
            process_problem=process_problem,
        )
