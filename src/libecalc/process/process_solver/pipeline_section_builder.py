"""
Build solver-ready PipelineSection objects from process-owned preparation input.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import assert_never

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.process.process_pipeline.process_pipeline import ProcessPipeline, ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy, AntiSurgeType
from libecalc.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.pipeline_section_build_input import (
    PipelineSectionBuildProblem,
    PipelineSectionBuildProblemSection,
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


def build_pipeline_sections(
    process_pipeline: ProcessPipeline,
    process_problem: PipelineSectionBuildProblem,
    root_finding_strategy: RootFindingStrategy | None = None,
) -> list[PipelineSection]:
    """Build PipelineSection objects with runner, shaft and solver strategies resolved."""
    if process_problem.process_pipeline_id != process_pipeline.get_id():
        raise EcalcValidationException(
            "Cannot build pipeline sections: process problem belongs to a different process pipeline."
        )

    root_finding_strategy = root_finding_strategy or ScipyRootFindingStrategy()
    pipeline_units = process_pipeline.get_process_units()

    context = _PipelineSectionBuildContext(
        process_pipeline_id=process_pipeline.get_id(),
        pipeline_units=pipeline_units,
        pipeline_unit_ids=frozenset(unit.get_id() for unit in pipeline_units),
        problem_configuration_handlers=process_problem.configuration_handlers,
        root_finding_strategy=root_finding_strategy,
    )

    return [
        _PipelineSectionBuilder(context=context, process_problem_section=section).build()
        for section in process_problem.process_problem_sections
    ]


@dataclass(frozen=True)
class _PipelineSectionBuildContext:
    process_pipeline_id: ProcessPipelineId
    pipeline_units: Sequence[ProcessUnit]
    pipeline_unit_ids: frozenset[ProcessUnitId]
    problem_configuration_handlers: Sequence[ConfigurationHandler]
    root_finding_strategy: RootFindingStrategy


class _PipelineSectionBuilder:
    def __init__(
        self,
        context: _PipelineSectionBuildContext,
        process_problem_section: PipelineSectionBuildProblemSection,
    ) -> None:
        self._context = context
        self._section_unit_ids = frozenset(process_problem_section.process_unit_ids)
        self._section_handlers = process_problem_section.configuration_handlers
        self._recirculation_loops = [
            handler for handler in self._section_handlers if isinstance(handler, RecirculationLoop)
        ]
        self._pressure_control_type: PressureControlType = process_problem_section.constraint.pressure_control.type
        self._anti_surge_type: AntiSurgeType = process_problem_section.constraint.anti_surge.type
        self._choke_handler = self._get_choke_handler()

    def build(self) -> PipelineSection:
        section_units = self._get_section_units()
        compressors = self._get_compressors(section_units)
        shaft = self._get_section_shaft(compressors)
        runner = ProcessPipelineRunner(
            units=section_units,
            configuration_handlers=[shaft, *self._section_handlers],
        )

        anti_surge_strategy = self._create_anti_surge_strategy(
            runner=runner,
            compressors=compressors,
        )
        pressure_control_strategy = self._create_pressure_control_strategy(
            runner=runner,
            compressors=compressors,
            anti_surge_strategy=anti_surge_strategy,
        )

        return PipelineSection(
            shaft_id=shaft.get_id(),
            process_pipeline_id=self._context.process_pipeline_id,
            runner=runner,
            anti_surge_strategy=anti_surge_strategy,
            pressure_control_strategy=pressure_control_strategy,
            speed_boundary=shaft.get_speed_boundary(),
            root_finding_strategy=self._context.root_finding_strategy,
        )

    def _get_choke_handler(self) -> ChokeConfigurationHandler | None:
        choke_handlers = [
            handler for handler in self._section_handlers if isinstance(handler, ChokeConfigurationHandler)
        ]

        if len(choke_handlers) > 1:
            raise EcalcValidationException("A pipeline section can only have one choke configuration handler.")

        return choke_handlers[0] if choke_handlers else None

    def _get_section_units(self) -> list[ProcessUnit]:
        missing_ids = self._section_unit_ids - self._context.pipeline_unit_ids
        if missing_ids:
            raise EcalcValidationException(f"Process section references units not found in pipeline: {missing_ids}")

        return [unit for unit in self._context.pipeline_units if unit.get_id() in self._section_unit_ids]

    @staticmethod
    def _get_compressors(section_units: Sequence[ProcessUnit]) -> list[Compressor]:
        compressors = [unit for unit in section_units if isinstance(unit, Compressor)]
        if not compressors:
            raise EcalcValidationException("Pipeline section builder only supports sections with compressors.")
        return compressors

    def _get_section_shaft(self, compressors: Sequence[Compressor]) -> Shaft:
        compressor_ids = {compressor.get_id() for compressor in compressors}

        matching_shafts = [
            handler
            for handler in self._context.problem_configuration_handlers
            if isinstance(handler, Shaft) and compressor_ids <= set(handler.get_compressor_ids())
        ]

        if len(matching_shafts) != 1:
            raise EcalcValidationException("PipelineSection build requires exactly one matching shaft.")

        return matching_shafts[0]

    def _get_required_choke_handler(self, pressure_control_type: PressureControlType) -> ChokeConfigurationHandler:
        if self._choke_handler is None:
            raise EcalcValidationException(f"{pressure_control_type} requires a choke configuration handler.")
        return self._choke_handler

    def _create_anti_surge_strategy(
        self,
        runner: ProcessPipelineRunner,
        compressors: Sequence[Compressor],
    ) -> AntiSurgeStrategy:
        match self._anti_surge_type:
            case AntiSurgeType.COMMON_ASV:
                return CommonASVAntiSurgeStrategy(
                    simulator=runner,
                    root_finding_strategy=self._context.root_finding_strategy,
                    first_compressor=compressors[0],
                    recirculation_loop_id=self._recirculation_loops[0].get_id(),
                )
            case AntiSurgeType.INDIVIDUAL_ASV:
                return IndividualASVAntiSurgeStrategy(
                    simulator=runner,
                    recirculation_loop_ids=[loop.get_id() for loop in self._recirculation_loops],
                    compressors=compressors,
                )
            case AntiSurgeType.NO_ASV:
                raise EcalcValidationException(
                    "PipelineSection build requires compressor sections with ASV anti-surge; "
                    "NO_ASV is only valid for sections that are not solved as PipelineSections."
                )
            case _:
                assert_never(self._anti_surge_type)

    def _create_pressure_control_strategy(
        self,
        runner: ProcessPipelineRunner,
        compressors: Sequence[Compressor],
        anti_surge_strategy: AntiSurgeStrategy,
    ) -> PressureControlStrategy:
        match self._pressure_control_type:
            case "DOWNSTREAM_CHOKE":
                choke_handler = self._get_required_choke_handler("DOWNSTREAM_CHOKE")
                return DownstreamChokePressureControlStrategy(
                    simulator=runner,
                    choke_configuration_handler_id=choke_handler.get_id(),
                )
            case "UPSTREAM_CHOKE":
                choke_handler = self._get_required_choke_handler("UPSTREAM_CHOKE")
                return UpstreamChokePressureControlStrategy(
                    simulator=runner,
                    choke_configuration_handler_id=choke_handler.get_id(),
                    root_finding_strategy=self._context.root_finding_strategy,
                    anti_surge_strategy=anti_surge_strategy,
                )
            case "COMMON_ASV":
                return CommonASVPressureControlStrategy(
                    simulator=runner,
                    recirculation_loop_id=self._recirculation_loops[0].get_id(),
                    first_compressor=compressors[0],
                    root_finding_strategy=self._context.root_finding_strategy,
                )
            case "INDIVIDUAL_ASV_RATE":
                return IndividualASVRateControlStrategy(
                    simulator=runner,
                    recirculation_loop_ids=[loop.get_id() for loop in self._recirculation_loops],
                    compressors=compressors,
                    root_finding_strategy=self._context.root_finding_strategy,
                )
            case "INDIVIDUAL_ASV_PRESSURE":
                return IndividualASVPressureControlStrategy(
                    simulator=runner,
                    recirculation_loop_ids=[loop.get_id() for loop in self._recirculation_loops],
                    compressors=compressors,
                    root_finding_strategy=self._context.root_finding_strategy,
                )
            case _:
                assert_never(self._pressure_control_type)
