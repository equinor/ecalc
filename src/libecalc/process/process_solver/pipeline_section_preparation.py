"""
Prepare process problem sections for pipeline-section solving.

The preparation resolves section units and solver strategies into runtime
PipelineSection objects.
"""

from collections.abc import Sequence
from typing import assert_never

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.process.process_pipeline.process_pipeline import ProcessPipeline
from libecalc.process.process_pipeline.process_unit import ProcessUnit
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy, AntiSurgeType
from libecalc.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.pipeline_section_preparation_input import (
    PipelineSectionPreparationProblem,
    PipelineSectionPreparationProblemSection,
)
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


def prepare_pipeline_sections(
    process_pipeline: ProcessPipeline,
    process_problem: PipelineSectionPreparationProblem,
    root_finding_strategy: RootFindingStrategy | None = None,
) -> list[PipelineSection]:
    if process_problem.process_pipeline_id != process_pipeline.get_id():
        raise EcalcValidationException(
            "Cannot prepare pipeline sections: process problem belongs to a different process pipeline."
        )
    root_finding_strategy = root_finding_strategy or ScipyRootFindingStrategy()
    return [
        _assemble_pipeline_section(
            process_pipeline=process_pipeline,
            process_problem_section=section,
            problem_configuration_handlers=process_problem.configuration_handlers,
            root_finding_strategy=root_finding_strategy,
        )
        for section in process_problem.process_problem_sections
    ]


def _assemble_pipeline_section(
    process_pipeline: ProcessPipeline,
    process_problem_section: PipelineSectionPreparationProblemSection,
    problem_configuration_handlers: Sequence[ConfigurationHandler],
    root_finding_strategy: RootFindingStrategy,
) -> PipelineSection:

    section_units = _get_section_units(
        process_pipeline=process_pipeline,
        process_problem_section=process_problem_section,
    )
    compressors = [unit for unit in section_units if isinstance(unit, Compressor)]
    if not compressors:
        raise EcalcValidationException("Pipeline section preparation only supports sections with compressors.")

    shaft = _get_section_shaft(
        compressors=compressors,
        problem_configuration_handlers=problem_configuration_handlers,
    )

    section_handlers = list(process_problem_section.configuration_handlers)

    runner = ProcessPipelineRunner(
        units=section_units,
        configuration_handlers=[shaft, *section_handlers],
    )

    recirculation_loops = [h for h in section_handlers if isinstance(h, RecirculationLoop)]

    choke_handlers = [h for h in section_handlers if isinstance(h, ChokeConfigurationHandler)]
    if len(choke_handlers) > 1:
        raise EcalcValidationException("A pipeline section can only have one choke configuration handler.")
    choke_handler = choke_handlers[0] if choke_handlers else None

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

    return PipelineSection(
        shaft_id=shaft.get_id(),
        process_pipeline_id=process_pipeline.get_id(),
        runner=runner,
        anti_surge_strategy=anti_surge_strategy,
        pressure_control_strategy=pressure_control_strategy,
        speed_boundary=shaft.get_speed_boundary(),
        root_finding_strategy=root_finding_strategy,
    )


def _get_section_units(
    process_pipeline: ProcessPipeline,
    process_problem_section: PipelineSectionPreparationProblemSection,
) -> list[ProcessUnit]:
    """Return section units in process pipeline order."""
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
            return CommonASVPressureControlStrategy(
                simulator=runner,
                recirculation_loop_id=recirculation_loops[0].get_id(),
                first_compressor=compressors[0],
                root_finding_strategy=root_finding_strategy,
            )
        case "INDIVIDUAL_ASV_RATE":
            return IndividualASVRateControlStrategy(
                simulator=runner,
                recirculation_loop_ids=[loop.get_id() for loop in recirculation_loops],
                compressors=compressors,
                root_finding_strategy=root_finding_strategy,
            )
        case "INDIVIDUAL_ASV_PRESSURE":
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
            return CommonASVAntiSurgeStrategy(
                simulator=runner,
                root_finding_strategy=root_finding_strategy,
                first_compressor=compressors[0],
                recirculation_loop_id=recirculation_loops[0].get_id(),
            )
        case AntiSurgeType.INDIVIDUAL_ASV:
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
