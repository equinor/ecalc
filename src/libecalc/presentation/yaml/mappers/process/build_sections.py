from libecalc.common.ddd import value_object
from libecalc.presentation.yaml.mappers.process.process_section_validator import ProcessSectionValidator
from libecalc.presentation.yaml.mappers.process.process_partitioner import (
    ProcessSection,
    ProcessPartitioner,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import ProcessUnitReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlProcessConstraint
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
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
class WrappedSection:
    index: int
    process_units: list[ProcessUnit]
    configuration_handlers: list[ConfigurationHandler]
    pressure_control: str
    outlet_pressure: object


def _wrap_compressor_in_recirculation_loop(group: list[ProcessUnit]) -> tuple[RecirculationLoop, list[ProcessUnit]]:
    mixer, splitter = DirectMixer(), DirectSplitter()
    loop = RecirculationLoop(mixer=mixer, splitter=splitter)
    return loop, [mixer, *group, splitter]


def wrap_section(section_: ProcessSection, fluid_service: FluidService) -> WrappedSection:
    """Wrap a section's units into ASV/choke topology, producing solver-ready units + handlers."""
    handlers: list[ConfigurationHandler] = []

    if section_.anti_surge == "COMMON_ASV":
        loop, pipeline = _wrap_compressor_in_recirculation_loop(section_.units)
        handlers.append(loop)
    else:
        pipeline = []
        pending_units: list[
            ProcessUnit
        ] = []  # held until a boundary (compressor → wrapped; mixer/splitter/end → unwrapped)
        for unit in section_.units:
            if isinstance(unit, (Mixer, Splitter)):
                pipeline.extend(pending_units)  # units with no compressor: leave unwrapped
                pending_units = []  # start a new group
                pipeline.append(unit)  # mixer/splitter stays outside the loop
                continue
            pending_units.append(unit)  # hold until we reach the compressor
            if isinstance(unit, Compressor):
                loop, wrapped = _wrap_compressor_in_recirculation_loop(pending_units)
                handlers.append(loop)
                pipeline.extend(wrapped)  # add the wrapped group
                pending_units = []  # start a new group
        pipeline.extend(pending_units)  # units after the last compressor

    if section_.pressure_control in ("UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE"):
        choke = Choke(fluid_service=fluid_service)
        handlers.append(ChokeConfigurationHandler(choke=choke))
        if section_.pressure_control == "UPSTREAM_CHOKE":
            pipeline = [choke, *pipeline]
        else:
            pipeline = [*pipeline, choke]

    return WrappedSection(
        index=section_.index,
        process_units=pipeline,
        configuration_handlers=handlers,
        pressure_control=section_.pressure_control,
        outlet_pressure=section_.outlet_pressure,
    )


class ProcessSectionBuilder:
    """
    Core entry point: partition → validate → wrap.

    To move wrapping to the backend, call `partition_and_validate` from core and
    have the backend invoke `wrap_section` on the returned sections.
    """

    def __init__(self, fluid_service: FluidService):
        self._fluid_service = fluid_service
        self._partitioner = ProcessPartitioner()
        self._validator = ProcessSectionValidator()

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

    def build_sections(
        self,
        process_unit_map: dict[ProcessUnitId, ProcessUnit],
        unit_name_to_id: dict[ProcessUnitReference, ProcessUnitId],
        pipeline_constraints: list[YamlProcessConstraint],
    ) -> list[WrappedSection]:
        sections = self.partition_and_validate(
            process_unit_map=process_unit_map,
            unit_name_to_id=unit_name_to_id,
            pipeline_constraints=pipeline_constraints,
        )
        return [wrap_section(s, self._fluid_service) for s in sections]
