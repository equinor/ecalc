from dataclasses import dataclass
from uuid import UUID

from libecalc.domain.infrastructure.path_id import PathID
from libecalc.presentation.yaml.domain.yaml_component import YamlComponent
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath


@dataclass
class ComponentContext:
    yaml_path: YamlPath
    path_id: PathID


class MappingContext:
    def __init__(self):
        self._id_map: dict[UUID, ComponentContext] = {}
        self._yaml_path_map: dict[YamlPath, ComponentContext] = {}

    def register_yaml_component(self, yaml_path: YamlPath, path_id: PathID, yaml_component: YamlComponent):
        component_context = ComponentContext(
            yaml_path=yaml_path,
            path_id=path_id,
        )
        self._yaml_path_map[yaml_path] = component_context
        self._id_map[yaml_component.id] = component_context

    def get_component_name(self, yaml_path: YamlPath) -> str | None:
        component_context = self._yaml_path_map.get(yaml_path)
        if component_context is None:
            return None

        return component_context.path_id.get_name()
