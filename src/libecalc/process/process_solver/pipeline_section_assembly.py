"""
Prepare process problem sections for pipeline-section solving.

All ProcessProblemSections are preserved in order. Compressor sections are
assembled into runtime PipelineSection objects. Passive sections are retained with
their units, handlers and pressure targets for later process-level solving.
"""

from collections.abc import Sequence
from typing import assert_never

from libecalc.common.ddd import value_object
from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.time_utils import Period
from libecalc.ecalc_model.process_simulation import ProcessProblem, ProcessProblemSection
from libecalc.process.process_pipeline.process_pipeline import ProcessPipeline
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy, AntiSurgeType
from libecalc.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.process.process_solver.pressure_control.downstream_choke import DownstreamChokePressureControlStrategy
from libecalc.process.process_solver.pressure_control.individual_asv import (
    IndividualASVPressureControlStrategy,
    IndividualASVRateControlStrategy,
)
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import (
    PressureControlStrategy,
    PressureControlType,
)
from libecalc.process.process_solver.pressure_control.upstream_choke import UpstreamChokePressureControlStrategy
from libecalc.process.process_solver.process_pipeline_runner import ProcessPipelineRunner
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.process.process_solver.search_strategies import RootFindingStrategy, ScipyRootFindingStrategy
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.shaft import Shaft


@value_object
class PreparedActivePipelineSection:
    """
    Prepared compressor-backed section that can be solved as a runtime PipelineSection.
    Also includes period-dependent problem data needed when solving.

    PipelineSection contains solver wiring only; target pressure remains on the
    ProcessProblemSection because it is evaluated per period.
    """

    pipeline_section: PipelineSection
    process_problem_section: ProcessProblemSection

    def get_pressure_target(self, period: Period) -> FloatConstraint:
        return _get_pressure_target(self.process_problem_section, period)


@value_object
class PreparedPassivePipelineSection:
    """
    Prepared non-compressor section retained in section order.

    Passive sections have units, handlers and target pressure, but no shaft-speed
    requirement and no runtime PipelineSection.
    """

    process_units: list[ProcessUnit]
    configuration_handlers: Sequence[ConfigurationHandler]
    process_problem_section: ProcessProblemSection

    def get_pressure_target(self, period: Period) -> FloatConstraint:
        return _get_pressure_target(self.process_problem_section, period)


type PreparedPipelineSection = PreparedActivePipelineSection | PreparedPassivePipelineSection


# Public API
def prepare_pipeline_sections(
    process_pipeline: ProcessPipeline,
    process_problem: ProcessProblem,
    root_finding_strategy: RootFindingStrategy | None = None,
) -> list[PreparedPipelineSection]:
    if process_problem.process_pipeline_id != process_pipeline.get_id():
        raise EcalcValidationException(
            "Cannot prepare pipeline sections: process problem belongs to a different process pipeline."
        )
    return [
        _prepare_pipeline_section(
            process_pipeline=process_pipeline,
            process_problem_section=section,
            problem_configuration_handlers=process_problem.configuration_handlers,
            root_finding_strategy=root_finding_strategy,
        )
        for section in process_problem.process_problem_sections
    ]


# Private preparation/assembly flow
def _prepare_pipeline_section(
    process_pipeline: ProcessPipeline,
    process_problem_section: ProcessProblemSection,
    problem_configuration_handlers: Sequence[ConfigurationHandler],
    root_finding_strategy: RootFindingStrategy | None,
) -> PreparedPipelineSection:
    section_units = _get_section_units(
        process_pipeline=process_pipeline,
        process_problem_section=process_problem_section,
    )
    section_handlers = list(process_problem_section.configuration_handlers)

    _validate_section_handlers_belong_to_section(
        section_units=section_units,
        section_handlers=section_handlers,
    )
    _validate_target_belongs_to_section(
        target_process_unit_id=process_problem_section.constraint.target_process_unit_id,
        section_units=section_units,
    )

    if not any(isinstance(unit, Compressor) for unit in section_units):
        return PreparedPassivePipelineSection(
            process_units=section_units,
            configuration_handlers=section_handlers,
            process_problem_section=process_problem_section,
        )

    return _assemble_active_pipeline_section(
        process_pipeline=process_pipeline,
        process_problem_section=process_problem_section,
        problem_configuration_handlers=problem_configuration_handlers,
        root_finding_strategy=root_finding_strategy,
    )


def _assemble_active_pipeline_section(
    process_pipeline: ProcessPipeline,
    process_problem_section: ProcessProblemSection,
    problem_configuration_handlers: Sequence[ConfigurationHandler],
    root_finding_strategy: RootFindingStrategy | None = None,
) -> PreparedActivePipelineSection:
    if root_finding_strategy is None:
        root_finding_strategy = ScipyRootFindingStrategy()

    section_units = _get_section_units(
        process_pipeline=process_pipeline,
        process_problem_section=process_problem_section,
    )
    _validate_can_assemble_active_pipeline_section(section_units=section_units)

    compressors = [unit for unit in section_units if isinstance(unit, Compressor)]
    shaft = _get_section_shaft(
        compressors=compressors,
        problem_configuration_handlers=problem_configuration_handlers,
    )

    section_handlers = list(process_problem_section.configuration_handlers)

    # Shaft is problem-level; recirculation loops and choke handlers are section-local.
    runner = ProcessPipelineRunner(
        units=section_units,
        configuration_handlers=[shaft, *section_handlers],
    )

    recirculation_loops = [h for h in section_handlers if isinstance(h, RecirculationLoop)]
    choke_handler = _get_choke_configuration_handler(section_handlers)

    anti_surge_strategy = _resolve_anti_surge_strategy(
        anti_surge_type=process_problem_section.constraint.anti_surge.type,
        runner=runner,
        compressors=compressors,
        recirculation_loops=recirculation_loops,
        root_finding_strategy=root_finding_strategy,
    )

    pressure_control_strategy = _resolve_pressure_control_strategy(
        pressure_control_type=process_problem_section.constraint.pressure_control.type,
        runner=runner,
        compressors=compressors,
        recirculation_loops=recirculation_loops,
        choke_configuration_handler=choke_handler,
        anti_surge_strategy=anti_surge_strategy,
        root_finding_strategy=root_finding_strategy,
    )

    pipeline_section = PipelineSection(
        shaft_id=shaft.get_id(),
        process_pipeline_id=process_pipeline.get_id(),
        runner=runner,
        anti_surge_strategy=anti_surge_strategy,
        pressure_control_strategy=pressure_control_strategy,
        speed_boundary=shaft.get_speed_boundary(),
        root_finding_strategy=root_finding_strategy,
    )
    return PreparedActivePipelineSection(
        pipeline_section=pipeline_section,
        process_problem_section=process_problem_section,
    )


# Section lookup
def _get_section_units(
    process_pipeline: ProcessPipeline,
    process_problem_section: ProcessProblemSection,
) -> list[ProcessUnit]:
    """Return section units in process pipeline order."""
    if not process_problem_section.process_unit_ids:
        raise EcalcValidationException("Process section must reference at least one process unit.")

    duplicate_unit_ids = {
        unit_id
        for unit_id in process_problem_section.process_unit_ids
        if process_problem_section.process_unit_ids.count(unit_id) > 1
    }
    if duplicate_unit_ids:
        raise EcalcValidationException(f"Process section references duplicate units: {duplicate_unit_ids}")

    section_unit_ids = set(process_problem_section.process_unit_ids)
    pipeline_units = process_pipeline.get_process_units()
    pipeline_unit_ids = {unit.get_id() for unit in pipeline_units}

    missing_ids = section_unit_ids - pipeline_unit_ids
    if missing_ids:
        raise EcalcValidationException(f"Process section references units not found in pipeline: {missing_ids}")

    return [unit for unit in pipeline_units if unit.get_id() in section_unit_ids]


def _get_section_shaft(
    compressors: Sequence[Compressor],
    problem_configuration_handlers: Sequence[ConfigurationHandler],
) -> Shaft:
    compressor_ids = {compressor.get_id() for compressor in compressors}

    matching_shafts = [
        handler
        for handler in problem_configuration_handlers
        if isinstance(handler, Shaft) and compressor_ids <= set(handler.get_compressor_ids())
    ]

    if len(matching_shafts) != 1:
        raise EcalcValidationException("PipelineSection assembly requires exactly one matching shaft.")

    return matching_shafts[0]


def _get_choke_configuration_handler(
    configuration_handlers: Sequence[ConfigurationHandler],
) -> ChokeConfigurationHandler | None:
    handlers = [h for h in configuration_handlers if isinstance(h, ChokeConfigurationHandler)]
    if len(handlers) > 1:
        raise EcalcValidationException("A pipeline section can only have one choke configuration handler.")
    return handlers[0] if handlers else None


# Strategy resolution
def _resolve_pressure_control_strategy(
    pressure_control_type: PressureControlType,
    runner: ProcessPipelineRunner,
    compressors: Sequence[Compressor],
    recirculation_loops: Sequence[RecirculationLoop],
    choke_configuration_handler: ChokeConfigurationHandler | None,
    anti_surge_strategy: AntiSurgeStrategy,
    root_finding_strategy: RootFindingStrategy,
) -> PressureControlStrategy:
    match pressure_control_type:
        case "DOWNSTREAM_CHOKE":
            if choke_configuration_handler is None:
                raise EcalcValidationException("DOWNSTREAM_CHOKE requires a choke configuration handler.")
            return DownstreamChokePressureControlStrategy(
                simulator=runner,
                choke_configuration_handler_id=choke_configuration_handler.get_id(),
            )
        case "UPSTREAM_CHOKE":
            if choke_configuration_handler is None:
                raise EcalcValidationException("UPSTREAM_CHOKE requires a choke configuration handler.")
            return UpstreamChokePressureControlStrategy(
                simulator=runner,
                choke_configuration_handler_id=choke_configuration_handler.get_id(),
                root_finding_strategy=root_finding_strategy,
                anti_surge_strategy=anti_surge_strategy,
            )
        case "COMMON_ASV":
            _validate_common_asv(compressors=compressors, recirculation_loops=recirculation_loops)
            return CommonASVPressureControlStrategy(
                simulator=runner,
                recirculation_loop_id=recirculation_loops[0].get_id(),
                first_compressor=compressors[0],
                root_finding_strategy=root_finding_strategy,
            )
        case "INDIVIDUAL_ASV_RATE":
            _validate_individual_asv(compressors=compressors, recirculation_loops=recirculation_loops)
            return IndividualASVRateControlStrategy(
                simulator=runner,
                recirculation_loop_ids=[loop.get_id() for loop in recirculation_loops],
                compressors=compressors,
                root_finding_strategy=root_finding_strategy,
            )
        case "INDIVIDUAL_ASV_PRESSURE":
            _validate_individual_asv(compressors=compressors, recirculation_loops=recirculation_loops)
            return IndividualASVPressureControlStrategy(
                simulator=runner,
                recirculation_loop_ids=[loop.get_id() for loop in recirculation_loops],
                compressors=compressors,
                root_finding_strategy=root_finding_strategy,
            )
        case _:
            assert_never(pressure_control_type)


def _resolve_anti_surge_strategy(
    anti_surge_type: AntiSurgeType,
    runner: ProcessPipelineRunner,
    compressors: Sequence[Compressor],
    recirculation_loops: Sequence[RecirculationLoop],
    root_finding_strategy: RootFindingStrategy,
) -> AntiSurgeStrategy:
    match anti_surge_type:
        case AntiSurgeType.COMMON_ASV:
            _validate_common_asv(compressors=compressors, recirculation_loops=recirculation_loops)
            return CommonASVAntiSurgeStrategy(
                simulator=runner,
                root_finding_strategy=root_finding_strategy,
                first_compressor=compressors[0],
                recirculation_loop_id=recirculation_loops[0].get_id(),
            )
        case AntiSurgeType.INDIVIDUAL_ASV:
            _validate_individual_asv(compressors=compressors, recirculation_loops=recirculation_loops)
            return IndividualASVAntiSurgeStrategy(
                simulator=runner,
                recirculation_loop_ids=[loop.get_id() for loop in recirculation_loops],
                compressors=compressors,
            )
        case AntiSurgeType.NO_ASV:
            raise EcalcValidationException(
                "PipelineSection assembly requires compressor sections with ASV anti-surge; "
                "NO_ASV is only valid for sections that are not solved as PipelineSections."
            )
        case _:
            assert_never(anti_surge_type)


# Assembly checks
def _validate_can_assemble_active_pipeline_section(section_units: Sequence[ProcessUnit]) -> None:
    if not any(isinstance(unit, Compressor) for unit in section_units):
        raise EcalcValidationException(
            "Process problem section cannot be assembled as PipelineSection because it contains no compressor. "
            "Non-compressor sections are valid process problem sections, but cannot be assembled as active PipelineSection."
        )


def _validate_common_asv(
    compressors: Sequence[Compressor],
    recirculation_loops: Sequence[RecirculationLoop],
) -> None:
    if len(recirculation_loops) != 1:
        raise EcalcValidationException("COMMON_ASV requires exactly one recirculation loop.")
    if not compressors:
        raise EcalcValidationException("COMMON_ASV requires at least one compressor.")


def _validate_individual_asv(
    compressors: Sequence[Compressor],
    recirculation_loops: Sequence[RecirculationLoop],
) -> None:
    if len(recirculation_loops) != len(compressors):
        raise EcalcValidationException("INDIVIDUAL_ASV requires one recirculation loop per compressor in the section.")


def _validate_section_handlers_belong_to_section(
    section_units: Sequence[ProcessUnit],
    section_handlers: Sequence[ConfigurationHandler],
) -> None:
    section_unit_ids = {unit.get_id() for unit in section_units}

    for handler in section_handlers:
        if isinstance(handler, RecirculationLoop):
            referenced_unit_ids = {handler.get_mixer_id(), handler.get_splitter_id()}
        elif isinstance(handler, ChokeConfigurationHandler):
            referenced_unit_ids = {handler.get_choke_id()}
        else:
            raise EcalcValidationException(
                f"Unsupported section configuration handler {handler.get_id()} of type {type(handler).__name__}."
            )

        missing_unit_ids = referenced_unit_ids - section_unit_ids
        if missing_unit_ids:
            raise EcalcValidationException(
                f"Section configuration handler {handler.get_id()} references units that do not exist in the section: "
                f"{missing_unit_ids}"
            )


def _validate_target_belongs_to_section(
    target_process_unit_id: ProcessUnitId,
    section_units: Sequence[ProcessUnit],
) -> None:
    section_unit_ids = {unit.get_id() for unit in section_units}
    if target_process_unit_id not in section_unit_ids:
        raise EcalcValidationException(
            f"Section pressure target references a unit that does not exist in the section: {target_process_unit_id}"
        )


# Pressure target extraction
def _get_pressure_target(process_problem_section: ProcessProblemSection, period: Period) -> FloatConstraint:
    outlet_pressure = process_problem_section.constraint.outlet_pressure

    matches = [
        outlet_pressure_value
        for expression_period, outlet_pressure_value in zip(
            outlet_pressure.get_periods(),
            outlet_pressure.get_masked_values(),
            strict=True,
        )
        if period in expression_period
    ]

    if not matches:
        raise EcalcValidationException(f"No outlet pressure target found for period {period}.")
    if len(matches) > 1:
        raise EcalcValidationException(f"Multiple outlet pressure targets found for period {period}.")

    return FloatConstraint(matches[0])
