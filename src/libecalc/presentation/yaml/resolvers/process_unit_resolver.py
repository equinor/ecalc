from dataclasses import dataclass

from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import YamlProcessUnitItem
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import ProcessUnitInstanceName
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import YamlProcessUnit


@dataclass(frozen=True)
class ResolvedProcessUnitItem:
    name: ProcessUnitInstanceName | None
    specification: YamlProcessUnit


class ProcessUnitResolver:
    def __init__(self, references: ReferenceService):
        self._references = references

    def resolve(self, item: YamlProcessUnitItem) -> ResolvedProcessUnitItem:
        specification = self._references.get_process_unit(item.target) if isinstance(item.target, str) else item.target
        return ResolvedProcessUnitItem(
            name=item.name,
            specification=specification,
        )
