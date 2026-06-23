from libecalc.common.ddd import value_object
from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import ProcessUnitReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlProcessConstraint
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType
from libecalc.process.process_units.compressor import Compressor


@value_object
class PipelineConstraintSection:
    """
    A contiguous range of process units governed by one constraint.

    Pure data: indices + units + the section's strategies/target. No wrapping.
    """

    index: int
    start: int
    end: int  # inclusive
    units: list[ProcessUnit]
    anti_surge: AntiSurgeType | None
    pressure_control: PressureControlType
    outlet_pressure: YamlExpressionType

    @property
    def is_first(self) -> bool:
        return self.start == 0


class PipelineSectionPartitioner:
    """
    Splits process units ino pipeline sections based on constraints.
    """

    @staticmethod
    def partition(
        process_unit_map: dict[ProcessUnitId, ProcessUnit],
        unit_name_to_id: dict[ProcessUnitReference, ProcessUnitId],
        pipeline_constraints: list[YamlProcessConstraint],
    ) -> list[PipelineConstraintSection]:
        ordered_unit_ids = list(process_unit_map.keys())
        ordered_units = list(process_unit_map.values())
        index_of = {uid: i for i, uid in enumerate(ordered_unit_ids)}

        outlet_indices: list[int] = []
        for constraint in pipeline_constraints:
            if constraint.unit is None:
                outlet_indices.append(len(ordered_units) - 1)
                continue
            unit_id = unit_name_to_id.get(constraint.unit)
            if unit_id is None:
                raise EcalcValidationException(f"Constraint references unknown unit '{constraint.unit}'.")
            outlet_indices.append(index_of[unit_id])

        if len(set(outlet_indices)) != len(outlet_indices):
            raise EcalcValidationException("Two constraints cannot point to the same unit.")

        if outlet_indices != sorted(outlet_indices):
            raise EcalcValidationException(
                "Constraints must be listed in pipeline order (each constraint's unit must come "
                "after the previous constraint's unit)."
            )

        last_constraint_index = outlet_indices[-1]
        trailing_units = ordered_units[last_constraint_index + 1 :]
        if any(isinstance(u, Compressor) for u in trailing_units):
            raise EcalcValidationException(
                "A compressor cannot appear after the last constraint; "
                "every compressor must be covered by a constraint."
            )

        sections: list[PipelineConstraintSection] = []
        start = 0
        for i, (end, constraint) in enumerate(zip(outlet_indices, pipeline_constraints)):
            is_last = i == len(pipeline_constraints) - 1
            # Constraints are validated to be in pipeline order, so each section ends at its
            # constraint's unit. The last section extends to the end of the pipeline so any
            # trailing conditioning units (no compressor) are absorbed into it.
            section_end = len(ordered_unit_ids) - 1 if is_last else end  # last section absorbs trailing units
            unit_ids = ordered_unit_ids[start : section_end + 1]
            sections.append(
                PipelineConstraintSection(
                    index=i,
                    start=start,
                    end=section_end,
                    units=[process_unit_map[uid] for uid in unit_ids],
                    anti_surge=constraint.anti_surge,
                    pressure_control=constraint.pressure_control,
                    outlet_pressure=constraint.outlet_pressure,
                )
            )
            start = section_end + 1
        return sections
