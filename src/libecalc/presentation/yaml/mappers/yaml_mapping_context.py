from uuid import UUID

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.domain.regularity import Regularity
from libecalc.presentation.yaml.domain.category_service import CategoryService
from libecalc.presentation.yaml.domain.default_process_service import DefaultProcessService
from libecalc.presentation.yaml.domain.energy_container_energy_model_builder import EnergyContainerEnergyModelBuilder
from libecalc.presentation.yaml.domain.yaml_component import YamlComponent
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath


class MappingContext(CategoryService):
    def __init__(self, target_period: Period):
        self._yaml_path_map: dict[YamlPath, YamlComponent] = {}
        self._yaml_component_map: dict[UUID, YamlComponent] = {}

        self._target_period = target_period
        self._process_service = DefaultProcessService()
        self._energy_container_energy_model_builder = EnergyContainerEnergyModelBuilder()

        self._regularity_map: dict[UUID, Regularity] = {}

    def get_energy_container_energy_model_builder(self) -> EnergyContainerEnergyModelBuilder:
        return self._energy_container_energy_model_builder

    def register_yaml_component(self, yaml_path: YamlPath, yaml_component: YamlComponent):
        self._yaml_path_map[yaml_path] = yaml_component
        self._yaml_component_map[yaml_component.id] = yaml_component

    def get_component_name_from_yaml_path(self, yaml_path: YamlPath) -> str | None:
        component_context = self._yaml_path_map.get(yaml_path)
        if component_context is None:
            return None

        return component_context.name

    def get_category(self, id: UUID) -> TemporalModel[str] | None:
        yaml_component = self._yaml_component_map[id]
        category = yaml_component.category
        if category is None:
            return None
        return TemporalModel.create(category, target_period=self._target_period)

    def register_regularity(self, container_id: UUID, regularity: Regularity):
        self._regularity_map[container_id] = regularity

    def get_regularity(self, container_id: UUID) -> Regularity:
        return self._regularity_map[container_id]
