from uuid import UUID

from libecalc.common.time_utils import Period
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.process_service import ProcessService
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.presentation.yaml.domain.ecalc_component import (
    EcalcComponent,
    EvalInputType,
    ModelType,
    RegisteredComponent,
)


class DefaultProcessService(ProcessService):
    def __init__(self):
        self._registered_components: dict[UUID, RegisteredComponent] = {}
        self._consumer_to_model_map: dict[tuple[UUID, Period], list[UUID]] = {}

    def get_consumer_to_model_map(self) -> dict[tuple[UUID, Period], list[UUID]]:
        return self._consumer_to_model_map

    def get_components_for_consumer(self, consumer_id: UUID, period: Period) -> list[RegisteredComponent]:
        component_ids = self._consumer_to_model_map.get((consumer_id, period), [])
        return [self._registered_components[component_id] for component_id in component_ids]

    def get_compressor_process_systems(self) -> dict[UUID, RegisteredComponent]:
        return {
            reg.ecalc_component.id: reg
            for reg in self._registered_components.values()
            if self._is_compressor_process_system(reg.model)
        }

    def get_pump_process_systems(self) -> dict[UUID, RegisteredComponent]:
        return {
            reg.ecalc_component.id: reg
            for reg in self._registered_components.values()
            if isinstance(reg.model, PumpModel)
        }

    def get_compressors_sampled(self) -> dict[UUID, RegisteredComponent]:
        return {
            reg.ecalc_component.id: reg
            for reg in self._registered_components.values()
            if self._is_compressor_sampled(reg.model)
        }

    def map_model_to_consumer(self, consumer_id: UUID, period: Period, component_ids: list[UUID]):
        self._consumer_to_model_map[(consumer_id, period)] = component_ids

    def register_component(
        self,
        ecalc_component: EcalcComponent,
        model: ModelType,
        evaluation_input: EvalInputType | None = None,
        consumer_system_id: UUID | None = None,
    ):
        reg = RegisteredComponent(
            ecalc_component=ecalc_component,
            model=model,
            evaluation_input=evaluation_input,
            consumer_system_id=consumer_system_id,
        )
        self._registered_components[ecalc_component.id] = reg

    @staticmethod
    def _is_compressor_process_system(model: ModelType) -> bool:
        if isinstance(model, CompressorTrainModel):
            return True
        if isinstance(model, CompressorWithTurbineModel) and isinstance(model.compressor_model, CompressorTrainModel):
            return True
        return False

    @staticmethod
    def _is_compressor_sampled(model: ModelType) -> bool:
        if isinstance(model, CompressorModelSampled):
            return True
        if isinstance(model, CompressorWithTurbineModel) and isinstance(model.compressor_model, CompressorModelSampled):
            return True
        return False
