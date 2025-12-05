from uuid import UUID

from libecalc.common.time_utils import Period
from libecalc.domain.ecalc_component import EcalcComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSettingExpressions,
)
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.evaluation_input import (
    CompressorEvaluationInput,
    CompressorSampledEvaluationInput,
    ConsumerSystemOperationalInput,
    PumpEvaluationInput,
)
from libecalc.domain.process.process_service import ProcessService
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor
from libecalc.presentation.yaml.domain.consumer_system_registry import ConsumerSystemRegistry
from libecalc.presentation.yaml.domain.ecalc_components import (
    CompressorProcessSystemComponent,
    CompressorSampledComponent,
    PumpProcessSystemComponent,
)


class DefaultProcessService(ProcessService):
    def __init__(self):
        self._compressor_process_systems: dict[UUID, CompressorTrainModel | CompressorWithTurbineModel] = {}
        self._pump_process_systems: dict[UUID, PumpModel] = {}
        self._compressors_sampled: dict[UUID, CompressorModelSampled | CompressorWithTurbineModel] = {}
        self._evaluation_inputs: dict[
            UUID, CompressorEvaluationInput | CompressorSampledEvaluationInput | PumpEvaluationInput
        ] = {}
        self._consumer_to_model_map: dict[tuple[UUID, Period], list[UUID]] = {}
        self._ecalc_components: dict[UUID, EcalcComponent] = {}
        self._consumer_system_registry = ConsumerSystemRegistry()

    def get_evaluation_inputs(
        self,
    ) -> dict[UUID, CompressorEvaluationInput | CompressorSampledEvaluationInput | PumpEvaluationInput]:
        return self._evaluation_inputs

    def get_compressor_process_systems(self) -> dict[UUID, CompressorTrainModel]:
        return self._compressor_process_systems

    def get_pump_process_systems(self) -> dict[UUID, PumpModel]:
        return self._pump_process_systems

    def get_compressors_sampled(self) -> dict[UUID, CompressorModelSampled | CompressorWithTurbineModel]:
        return self._compressors_sampled

    def get_ecalc_components(self) -> dict[UUID, EcalcComponent]:
        return self._ecalc_components

    def get_consumer_to_model_map(self) -> dict[tuple[UUID, Period], list[UUID]]:
        return self._consumer_to_model_map

    def get_consumer_system_to_component_ids(self) -> dict[UUID, list[UUID]]:
        return self._consumer_system_registry.get_consumer_system_to_component_ids()

    def get_consumer_system_to_consumer_map(self) -> dict[UUID, UUID]:
        return self._consumer_system_registry.get_consumer_system_to_consumer_map()

    def get_consumer_system_to_period_map(self) -> dict[UUID, Period]:
        return self._consumer_system_registry.get_consumer_system_to_period_map()

    def get_consumer_system_operational_input(self) -> dict[UUID, ConsumerSystemOperationalInput]:
        return self._consumer_system_registry.get_consumer_system_operational_input()

    def get_consumer_system_all_operational_settings(
        self,
    ) -> dict[UUID, list[ConsumerSystemOperationalSettingExpressions]]:
        return self._consumer_system_registry.get_all_operational_settings()

    def get_model_by_id(self, model_id: UUID):
        """
        Retrieve a model (compressor, pump, or sampled) by its id.
        Returns None if not found.
        """
        if model_id in self._compressor_process_systems:
            return self._compressor_process_systems[model_id]
        if model_id in self._pump_process_systems:
            return self._pump_process_systems[model_id]
        if model_id in self._compressors_sampled:
            return self._compressors_sampled[model_id]
        return None

    def register_compressor_process_system(
        self,
        ecalc_component: EcalcComponent,
        compressor_process_system: CompressorTrainModel | CompressorWithTurbineModel,
        evaluation_input: CompressorEvaluationInput = None,
    ):
        self._ecalc_components[ecalc_component.id] = ecalc_component
        self._compressor_process_systems[ecalc_component.id] = compressor_process_system
        if evaluation_input is not None:
            self._evaluation_inputs[ecalc_component.id] = evaluation_input

    def register_pump_process_system(
        self,
        ecalc_component: EcalcComponent,
        pump_process_system: PumpModel,
        evaluation_input: PumpEvaluationInput = None,
    ):
        self._ecalc_components[ecalc_component.id] = ecalc_component
        self._pump_process_systems[ecalc_component.id] = pump_process_system
        if evaluation_input is not None:
            self._evaluation_inputs[ecalc_component.id] = evaluation_input

    def register_compressor_sampled(
        self,
        ecalc_component: EcalcComponent,
        compressor_sampled: CompressorModelSampled | CompressorWithTurbineModel,
        evaluation_input: CompressorSampledEvaluationInput = None,
    ):
        self._ecalc_components[ecalc_component.id] = ecalc_component
        self._compressors_sampled[ecalc_component.id] = compressor_sampled
        if evaluation_input is not None:
            self._evaluation_inputs[ecalc_component.id] = evaluation_input

    def register_consumer_system(
        self,
        system_id: UUID,
        component_ids: list[UUID],
        consumer_id: UUID,
        power_loss_factor: TimeSeriesPowerLossFactor,
    ):
        self._consumer_system_registry.register_consumer_system(
            consumer_id=consumer_id,
            system_id=system_id,
            component_ids=component_ids,
            power_loss_factor=power_loss_factor,
        )

    def register_consumer_system_operational_input(
        self, system_id: UUID, operational_input: ConsumerSystemOperationalInput
    ):
        self._consumer_system_registry.register_consumer_system_operational_input(
            system_id=system_id, operational_input=operational_input
        )

    def register_consumer_system_period(self, system_id: UUID, period: Period):
        self._consumer_system_registry.register_consumer_system_period(system_id=system_id, period=period)

    def register_consumer_system_all_operational_settings(
        self, system_id: UUID, operational_settings: list[ConsumerSystemOperationalSettingExpressions]
    ):
        self._consumer_system_registry.register_all_operational_settings(
            system_id=system_id, operational_settings=operational_settings
        )

    def map_model_to_consumer(
        self,
        consumer_id: UUID,
        period: Period,
        ecalc_component: CompressorProcessSystemComponent | PumpProcessSystemComponent | CompressorSampledComponent,
    ):
        key = (consumer_id, period)
        # To handle multiple models in consumer systems:
        if key not in self._consumer_to_model_map:
            self._consumer_to_model_map[key] = []
        self._consumer_to_model_map[key].append(ecalc_component.id)

    def components_in_system(self, component_ids: list[UUID]) -> bool:
        return self._consumer_system_registry.components_in_system(component_ids=component_ids)

    def get_consumer_system_id_by_component_ids(self, component_ids: list[UUID]) -> UUID:
        return self._consumer_system_registry.get_system_id_by_component_ids(component_ids=component_ids)
