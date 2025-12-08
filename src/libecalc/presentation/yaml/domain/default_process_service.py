from uuid import UUID

from libecalc.common.time_utils import Period
from libecalc.domain.ecalc_component import EcalcComponent
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.evaluation_input import (
    CompressorEvaluationInput,
    CompressorSampledEvaluationInput,
    PumpEvaluationInput,
)
from libecalc.domain.process.process_service import ProcessService
from libecalc.domain.process.pump.pump import PumpModel
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
        self._consumer_to_model_map: dict[tuple[UUID, Period], UUID] = {}
        self._ecalc_components: dict[UUID, EcalcComponent] = {}

    @property
    def evaluation_inputs(
        self,
    ) -> dict[UUID, CompressorEvaluationInput | CompressorSampledEvaluationInput | PumpEvaluationInput]:
        return self._evaluation_inputs

    @property
    def compressor_process_systems(self) -> dict[UUID, CompressorTrainModel]:
        return self._compressor_process_systems

    @property
    def pump_process_systems(self) -> dict[UUID, PumpModel]:
        return self._pump_process_systems

    @property
    def compressors_sampled(self) -> dict[UUID, CompressorModelSampled | CompressorWithTurbineModel]:
        return self._compressors_sampled

    @property
    def ecalc_components(self) -> dict[UUID, EcalcComponent]:
        return self._ecalc_components

    @property
    def consumer_to_model_map(self) -> dict[tuple[UUID, Period], UUID]:
        return self._consumer_to_model_map

    def register_compressor_process_system(
        self,
        ecalc_component: EcalcComponent,
        compressor_process_system: CompressorTrainModel | CompressorWithTurbineModel,
    ):
        self._ecalc_components[ecalc_component.id] = ecalc_component
        self._compressor_process_systems[ecalc_component.id] = compressor_process_system

    def register_pump_process_system(
        self,
        ecalc_component: EcalcComponent,
        pump_process_system: PumpModel,
    ):
        self._ecalc_components[ecalc_component.id] = ecalc_component
        self._pump_process_systems[ecalc_component.id] = pump_process_system

    def register_evaluation_input(
        self,
        ecalc_component: EcalcComponent,
        evaluation_input: CompressorEvaluationInput | CompressorSampledEvaluationInput | PumpEvaluationInput,
    ):
        self._evaluation_inputs[ecalc_component.id] = evaluation_input

    def register_compressor_sampled(
        self,
        ecalc_component: EcalcComponent,
        compressor_sampled: CompressorModelSampled | CompressorWithTurbineModel,
    ):
        self._ecalc_components[ecalc_component.id] = ecalc_component
        self._compressors_sampled[ecalc_component.id] = compressor_sampled

    def map_model_to_consumer(
        self,
        consumer_id: UUID,
        period: Period,
        ecalc_component: CompressorProcessSystemComponent | PumpProcessSystemComponent | CompressorSampledComponent,
    ):
        self.consumer_to_model_map[(consumer_id, period)] = ecalc_component.id

    def get_evaluation_input(
        self, model_id: UUID
    ) -> CompressorEvaluationInput | CompressorSampledEvaluationInput | PumpEvaluationInput:
        return self.evaluation_inputs.get(model_id)
