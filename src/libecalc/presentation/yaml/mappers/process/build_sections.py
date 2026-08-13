from libecalc.presentation.yaml.mappers.process.mapped_section_validator import MappedSectionValidator
from libecalc.presentation.yaml.mappers.process.process_partitioner import (
    MappedSection,
    ProcessPartitioner,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import InstanceReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlProcessConstraint
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_solver.section_assembly import assemble_process_section, AssembledSection


class ProcessSectionBuilder:
    """
    Partition → validate → assemble.

    To move section building to the backend, call `partition_and_validate` from core and
    have the backend invoke `assemble_section` over the returned sections.
    """

    def __init__(self):
        self._partitioner = ProcessPartitioner()
        self._validator = MappedSectionValidator()

    def partition_and_validate(
        self,
        process_unit_map: dict[ProcessUnitId, ProcessUnit],
        unit_name_to_id: dict[InstanceReference, ProcessUnitId],
        pipeline_constraints: list[YamlProcessConstraint],
    ) -> list[MappedSection]:
        sections = self._partitioner.partition(
            process_unit_map=process_unit_map,
            unit_name_to_id=unit_name_to_id,
            pipeline_constraints=pipeline_constraints,
        )
        self._validator.validate(sections)
        return sections

    @staticmethod
    def assemble_sections(mapped_sections: list[MappedSection], fluid_service: FluidService) -> list[AssembledSection]:
        return [
            assemble_process_section(
                process_units=s.process_units,
                anti_surge=s.constraint.anti_surge,
                pressure_control=s.constraint.pressure_control,
                fluid_service=fluid_service,
            )
            for s in mapped_sections
        ]
