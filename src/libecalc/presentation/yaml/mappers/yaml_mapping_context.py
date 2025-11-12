from uuid import UUID

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunction
from libecalc.domain.process.compressor.core import CompressorModel
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.entities.process_units.compressor.compressor import Compressor
from libecalc.domain.process.entities.process_units.liquid_remover.liquid_remover import LiquidRemover
from libecalc.domain.process.entities.process_units.pressure_modifier.pressure_modifier import (
    DifferentialPressureModifier,
)
from libecalc.domain.process.entities.process_units.rate_modifier.rate_modifier import RateModifier
from libecalc.domain.process.entities.process_units.temperature_setter.temperature_setter import TemperatureSetter
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.evaluation_input import CompressorEvaluationInput, PumpEvaluationInput
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.presentation.yaml.domain.category_service import CategoryService
from libecalc.presentation.yaml.domain.yaml_component import YamlComponent
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath


class MappingContext(CategoryService):
    def __init__(self, target_period: Period):
        self._yaml_path_map: dict[YamlPath, YamlComponent] = {}
        self._yaml_component_map: dict[UUID, YamlComponent] = {}
        self._process_systems: dict[UUID, CompressorModel] = {}
        self._process_units: dict[
            UUID, Compressor | Shaft | LiquidRemover | DifferentialPressureModifier | RateModifier | TemperatureSetter
        ] = {}
        self._simplified_process_units: dict[UUID, PumpModel | CompressorModelSampled | CompressorWithTurbineModel] = {}
        self._consumer_functions: dict[UUID, ConsumerFunction] = {}
        self._evaluation_input: dict[UUID, CompressorEvaluationInput] = {}
        self._consumer_to_model_map: dict[tuple[UUID, Period], UUID] = {}
        self._target_period = target_period

    def register_yaml_component(self, yaml_path: YamlPath, yaml_component: YamlComponent):
        self._yaml_path_map[yaml_path] = yaml_component
        self._yaml_component_map[yaml_component.id] = yaml_component

    def register_process_system(self, id: UUID, process_system: CompressorModel):
        self._process_systems[id] = process_system

    def register_process_unit(
        self,
        id: UUID,
        process_unit: Compressor
        | Shaft
        | LiquidRemover
        | DifferentialPressureModifier
        | RateModifier
        | TemperatureSetter,
    ):
        self._process_units[id] = process_unit

    def register_simplified_process_unit(
        self, id: UUID, simplified_process_unit: PumpModel | CompressorModelSampled | CompressorWithTurbineModel
    ):
        self._simplified_process_units[id] = simplified_process_unit

    def register_consumer_function(self, id: UUID, consumer_function: ConsumerFunction):
        self._consumer_functions[id] = consumer_function

    def register_evaluation_input(self, id: UUID, evaluation_input: CompressorEvaluationInput | PumpEvaluationInput):
        self._evaluation_input[id] = evaluation_input

    def map_model_to_consumer(self, consumer_id: UUID, period: Period, model_id: UUID):
        self._consumer_to_model_map[(consumer_id, period)] = model_id

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
