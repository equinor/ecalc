from libecalc.common.ddd import value_object
from libecalc.presentation.yaml.mappers.process.mapped_section_validator import MappedSectionValidator
from libecalc.presentation.yaml.mappers.process.process_partitioner import (
    MappedSection,
    ProcessPartitioner,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import ProcessUnitReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlProcessConstraint
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.mixer import Mixer
from libecalc.process.process_units.splitter import Splitter


@value_object
class AssembledSection:
    """Solver-ready process units + handlers for a given process section."""

    process_units: list[ProcessUnit]
    configuration_handlers: list[ConfigurationHandler]


def _wrap_compressor_in_recirculation_loop(
    process_units: list[ProcessUnit],
) -> tuple[RecirculationLoop, list[ProcessUnit]]:
    mixer, splitter = DirectMixer(), DirectSplitter()
    loop = RecirculationLoop(mixer=mixer, splitter=splitter)
    return loop, [mixer, *process_units, splitter]


def assemble_section(section: MappedSection, fluid_service: FluidService) -> AssembledSection:
    """Assemble a validated mapped section into solver-ready process units and configuration handlers."""
    handlers: list[ConfigurationHandler] = []

    if section.constraint.anti_surge == AntiSurgeType.COMMON_ASV:
        loop, solver_units = _wrap_compressor_in_recirculation_loop(section.process_units)
        handlers.append(loop)
    else:
        solver_units = []
        pending_units: list[
            ProcessUnit
        ] = []  # held until a boundary (compressor → assembled with ASV; mixer/splitter/end → unchanged)
        for unit in section.process_units:
            # Mixer and Splitter are always kept outside recirculation loops.
            if isinstance(unit, (Mixer, Splitter)):
                solver_units.extend(pending_units)  # units without a compressor are left unchanged
                pending_units = []
                solver_units.append(unit)  # mixer/splitter stays outside the loop
                continue
            pending_units.append(unit)  # hold until we reach the compressor
            if isinstance(unit, Compressor):
                loop, assembled = _wrap_compressor_in_recirculation_loop(pending_units)
                handlers.append(loop)
                solver_units.extend(assembled)  # add the assembled group
                pending_units = []
        solver_units.extend(pending_units)  # units after the last compressor

    if section.constraint.pressure_control in ("UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE"):
        choke = Choke(fluid_service=fluid_service)
        handlers.append(ChokeConfigurationHandler(choke=choke))
        if section.constraint.pressure_control == "UPSTREAM_CHOKE":
            solver_units = [choke, *solver_units]
        else:
            solver_units = [*solver_units, choke]

    return AssembledSection(
        process_units=solver_units,
        configuration_handlers=handlers,
    )


class ProcessSectionBuilder:
    """
    Partition → validate → assemble.

    To move section building to the backend, call `partition_and_validate` from core and
    have the backend invoke `assemble_section` over the returned sections.
    """

    def __init__(self, fluid_service: FluidService):
        self._fluid_service = fluid_service
        self._partitioner = ProcessPartitioner()
        self._validator = MappedSectionValidator()

    def partition_and_validate(
        self,
        process_unit_map: dict[ProcessUnitId, ProcessUnit],
        unit_name_to_id: dict[ProcessUnitReference, ProcessUnitId],
        pipeline_constraints: list[YamlProcessConstraint],
    ):
        sections = self._partitioner.partition(
            process_unit_map=process_unit_map,
            unit_name_to_id=unit_name_to_id,
            pipeline_constraints=pipeline_constraints,
        )
        self._validator.validate(sections)
        return sections

    def assemble_sections(self, mapped_sections: list[MappedSection]) -> list[AssembledSection]:
        return [assemble_section(s, self._fluid_service) for s in mapped_sections]
