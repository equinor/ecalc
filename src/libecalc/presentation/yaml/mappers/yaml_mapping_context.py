from dataclasses import dataclass
from uuid import UUID

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.presentation.yaml.domain.category_service import CategoryService
from libecalc.presentation.yaml.domain.yaml_component import YamlComponent
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath


@dataclass
class ComponentContext:
    yaml_path: YamlPath
    path_id: PathID


class MappingContext(CategoryService):
    def __init__(self, target_period: Period):
        self._id_map: dict[UUID, ComponentContext] = {}
        self._yaml_path_map: dict[YamlPath, ComponentContext] = {}
        self._yaml_component_map: dict[UUID, YamlComponent] = {}
        self._target_period = target_period

    def register_yaml_component(self, yaml_path: YamlPath, path_id: PathID, yaml_component: YamlComponent):
        component_context = ComponentContext(
            yaml_path=yaml_path,
            path_id=path_id,
        )
        self._yaml_path_map[yaml_path] = component_context
        self._id_map[yaml_component.id] = component_context
        self._yaml_component_map[yaml_component.id] = yaml_component

    def get_component_name_from_id(self, id: UUID) -> str | None:
        component_context = self._id_map.get(id)
        if component_context is None:
            return None

        return component_context.path_id.get_name()

    def get_component_name_from_yaml_path(self, yaml_path: YamlPath) -> str | None:
        component_context = self._yaml_path_map.get(yaml_path)
        if component_context is None:
            return None

        return component_context.path_id.get_name()

    def get_category(self, id: UUID) -> TemporalModel[str] | None:
        yaml_component = self._yaml_component_map[id]
        category = yaml_component.category
        if category is None:
            return None
        return TemporalModel.create(category, target_period=self._target_period)
