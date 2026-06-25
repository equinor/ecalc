from libecalc.common.ddd import value_object
from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import ProcessUnitReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlProcessConstraint
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_units.compressor import Compressor


@value_object
class MappedSection:
    """
    A group of consecutive process units governed by one constraint.

    Pure data: units + the section's constraint. No wrapping.
    """

    process_units: list[ProcessUnit]
    constraint: YamlProcessConstraint


class ProcessPartitioner:
    """
    Splits process units ino mapped process sections based on constraints.
    """

    @staticmethod
    def partition(
        process_unit_map: dict[ProcessUnitId, ProcessUnit],
        unit_name_to_id: dict[ProcessUnitReference, ProcessUnitId],
        pipeline_constraints: list[YamlProcessConstraint],
    ) -> list[MappedSection]:
        process_units = list(process_unit_map.values())
        constraint_by_unit_id: dict[ProcessUnitId, YamlProcessConstraint] = {}
        terminal_constraint: YamlProcessConstraint | None = None

        for constraint in pipeline_constraints:
            if constraint.process_unit is None:
                if terminal_constraint is not None:
                    raise EcalcValidationException("Only one constraint can target the process pipeline outlet.")
                terminal_constraint = constraint
                continue
            unit_id = unit_name_to_id.get(constraint.process_unit)
            if unit_id is None:
                raise EcalcValidationException(f"Constraint references unknown unit '{constraint.process_unit}'.")

            if unit_id in constraint_by_unit_id:
                raise EcalcValidationException(
                    f"Two constraints cannot point to the same unit '{constraint.process_unit}'."
                )
            constraint_by_unit_id[unit_id] = constraint

        sections: list[MappedSection] = []
        current_units: list[ProcessUnit] = []

        for process_unit in process_units:
            current_units.append(process_unit)

            constraint = constraint_by_unit_id.get(process_unit.get_id())
            if constraint is None:
                continue

            sections.append(
                MappedSection(
                    process_units=current_units,
                    constraint=constraint,
                )
            )
            current_units = []

        if terminal_constraint is not None:
            sections.append(
                MappedSection(
                    process_units=current_units,
                    constraint=terminal_constraint,
                )
            )
        elif any(isinstance(unit, Compressor) for unit in current_units):
            raise EcalcValidationException(
                "A compressor cannot appear after the last constraint; "
                "every compressor must be covered by a constraint."
            )
        elif sections and current_units:
            # trailing non-compressor units are absorbed into last section
            last = sections[-1]
            sections[-1] = MappedSection(
                process_units=[*last.process_units, *current_units],
                constraint=last.constraint,
            )

        return sections
