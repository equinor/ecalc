"""
Build solver-ready PipelineSection objects from process-owned preparation input.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import assert_never

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.process.process_pipeline.process_pipeline import (
    ProcessPipeline,
    ProcessPipelineId,
    ProcessPipelineSection,
    ProcessPipelineSectionId,
)
from libecalc.process.process_pipeline.process_unit import ProcessUnit
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy, AntiSurgeType
from libecalc.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.build_pipeline_sections_input import (
    BuildPipelineSectionsInput,
    BuildPipelineSectionInput,
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
    build_input: BuildPipelineSectionsInput,
    root_finding_strategy: RootFindingStrategy | None = None,
) -> list[PipelineSection]:
    """Build PipelineSection objects with runner, shaft and solver strategies resolved."""
    if build_input.process_pipeline_id != process_pipeline.get_id():
        raise EcalcValidationException(
            "Cannot build pipeline sections: build input belongs to a different process pipeline."
        )

    root_finding_strategy = root_finding_strategy or ScipyRootFindingStrategy()

    context = _PipelineSectionsBuildContext(
        process_pipeline_id=process_pipeline.get_id(),
        process_pipeline_sections_by_id={
            section.get_id(): section for section in process_pipeline.get_process_pipeline_sections()
        },
        configuration_handlers=build_input.configuration_handlers,
        root_finding_strategy=root_finding_strategy,
    )

    return [
        _PipelineSectionBuilder(context=context, section_input=section_input).build()
        for section_input in build_input.sections
    ]


@dataclass(frozen=True)
class _PipelineSectionsBuildContext:
    process_pipeline_id: ProcessPipelineId
    process_pipeline_sections_by_id: dict[ProcessPipelineSectionId, ProcessPipelineSection]
    configuration_handlers: Sequence[ConfigurationHandler]
    root_finding_strategy: RootFindingStrategy


class _PipelineSectionBuilder:
    def __init__(
        self,
        context: _PipelineSectionsBuildContext,
        section_input: BuildPipelineSectionInput,
    ) -> None:
        self._context = context
        self._process_pipeline_section_id = section_input.process_pipeline_section_id
        self._process_pipeline_section = self._get_process_pipeline_section()
        self._section_units = self._process_pipeline_section.get_process_units()
        self._section_unit_ids = {unit.get_id() for unit in self._section_units}
        self._compressors = self._get_compressors(self._section_units)
        self._shaft = self._get_section_shaft()
        self._section_handlers = self._get_section_configuration_handlers()
        self._recirculation_loops = [
            handler for handler in self._section_handlers if isinstance(handler, RecirculationLoop)
        ]
        self._choke_handler = self._get_choke_handler()
        self._pressure_control_type: PressureControlType = section_input.pressure_control
        self._anti_surge_type: AntiSurgeType = section_input.anti_surge
        self._runner = ProcessPipelineRunner(
            units=self._section_units,
            configuration_handlers=self._section_handlers,
        )

    def build(self) -> PipelineSection:
        anti_surge_strategy = self._create_anti_surge_strategy()
        pressure_control_strategy = self._create_pressure_control_strategy(
            anti_surge_strategy=anti_surge_strategy,
        )

        return PipelineSection(
            shaft_id=self._shaft.get_id(),
            process_pipeline_id=self._context.process_pipeline_id,
            process_pipeline_section_id=self._process_pipeline_section.get_id(),
            runner=self._runner,
            anti_surge_strategy=anti_surge_strategy,
            pressure_control_strategy=pressure_control_strategy,
            speed_boundary=self._shaft.get_speed_boundary(),
            root_finding_strategy=self._context.root_finding_strategy,
        )

    def _get_process_pipeline_section(self) -> ProcessPipelineSection:
        process_pipeline_section = self._context.process_pipeline_sections_by_id.get(self._process_pipeline_section_id)
        if process_pipeline_section is None:
            raise EcalcValidationException(
                f"Build input references pipeline section not found in pipeline: {self._process_pipeline_section_id}"
            )

        return process_pipeline_section

    @staticmethod
    def _get_compressors(section_units: Sequence[ProcessUnit]) -> list[Compressor]:
        compressors = [unit for unit in section_units if isinstance(unit, Compressor)]
        if not compressors:
            raise EcalcValidationException("Pipeline section builder only supports sections with compressors.")
        return compressors

    def _get_section_shaft(self) -> Shaft:
        compressor_ids = {compressor.get_id() for compressor in self._compressors}

        matching_shafts = [
            handler
            for handler in self._context.configuration_handlers
            if isinstance(handler, Shaft) and compressor_ids <= set(handler.get_compressor_ids())
        ]

        if len(matching_shafts) != 1:
            raise EcalcValidationException("PipelineSection build requires exactly one matching shaft.")

        return matching_shafts[0]

    def _get_section_configuration_handlers(self) -> list[ConfigurationHandler]:
        return [
            handler
            for handler in self._context.configuration_handlers
            if handler.get_id() == self._shaft.get_id()
            or (
                isinstance(handler, RecirculationLoop)
                and handler.get_mixer_id() in self._section_unit_ids
                and handler.get_splitter_id() in self._section_unit_ids
            )
            or (isinstance(handler, ChokeConfigurationHandler) and handler.get_choke_id() in self._section_unit_ids)
        ]

    def _get_choke_handler(self) -> ChokeConfigurationHandler | None:
        choke_handlers = [
            handler for handler in self._section_handlers if isinstance(handler, ChokeConfigurationHandler)
        ]

        if len(choke_handlers) > 1:
            raise EcalcValidationException("A pipeline section can only have one choke configuration handler.")

        return choke_handlers[0] if choke_handlers else None

    def _get_required_choke_handler(
        self,
        pressure_control_type: PressureControlType,
    ) -> ChokeConfigurationHandler:
        if self._choke_handler is None:
            raise EcalcValidationException(f"{pressure_control_type} requires a choke configuration handler.")
        return self._choke_handler

    def _create_anti_surge_strategy(
        self,
    ) -> AntiSurgeStrategy:
        match self._anti_surge_type:
            case AntiSurgeType.COMMON_ASV:
                return CommonASVAntiSurgeStrategy(
                    simulator=self._runner,
                    root_finding_strategy=self._context.root_finding_strategy,
                    first_compressor=self._compressors[0],
                    recirculation_loop_id=self._recirculation_loops[0].get_id(),
                )
            case AntiSurgeType.INDIVIDUAL_ASV:
                return IndividualASVAntiSurgeStrategy(
                    simulator=self._runner,
                    recirculation_loop_ids=[loop.get_id() for loop in self._recirculation_loops],
                    compressors=self._compressors,
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
        anti_surge_strategy: AntiSurgeStrategy,
    ) -> PressureControlStrategy:
        match self._pressure_control_type:
            case "DOWNSTREAM_CHOKE":
                choke_handler = self._get_required_choke_handler("DOWNSTREAM_CHOKE")
                return DownstreamChokePressureControlStrategy(
                    simulator=self._runner,
                    choke_configuration_handler_id=choke_handler.get_id(),
                )
            case "UPSTREAM_CHOKE":
                choke_handler = self._get_required_choke_handler("UPSTREAM_CHOKE")
                return UpstreamChokePressureControlStrategy(
                    simulator=self._runner,
                    choke_configuration_handler_id=choke_handler.get_id(),
                    root_finding_strategy=self._context.root_finding_strategy,
                    anti_surge_strategy=anti_surge_strategy,
                )
            case "COMMON_ASV":
                return CommonASVPressureControlStrategy(
                    simulator=self._runner,
                    recirculation_loop_id=self._recirculation_loops[0].get_id(),
                    first_compressor=self._compressors[0],
                    root_finding_strategy=self._context.root_finding_strategy,
                )
            case "INDIVIDUAL_ASV_RATE":
                return IndividualASVRateControlStrategy(
                    simulator=self._runner,
                    recirculation_loop_ids=[loop.get_id() for loop in self._recirculation_loops],
                    compressors=self._compressors,
                    root_finding_strategy=self._context.root_finding_strategy,
                )
            case "INDIVIDUAL_ASV_PRESSURE":
                return IndividualASVPressureControlStrategy(
                    simulator=self._runner,
                    recirculation_loop_ids=[loop.get_id() for loop in self._recirculation_loops],
                    compressors=self._compressors,
                    root_finding_strategy=self._context.root_finding_strategy,
                )
            case _:
                assert_never(self._pressure_control_type)
