from uuid import UUID

from libecalc.common.time_utils import Period
from libecalc.domain.ecalc_component import EcalcComponent
from libecalc.domain.process.compressor.core.base import CompressorModel, CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.evaluation_input import CompressorEvaluationInput, PumpEvaluationInput
from libecalc.domain.process.process_service import ProcessService
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.presentation.yaml.domain.ecalc_components import ProcessSystemComponent, SimplifiedProcessUnitComponent


class DefaultProcessService(ProcessService):
    def __init__(self):
        self._process_systems: dict[UUID, CompressorTrainModel] = {}
        self._simplified_process_units: dict[UUID, CompressorModelSampled | PumpModel | CompressorWithTurbineModel] = {}
        self._evaluation_inputs: dict[UUID, CompressorEvaluationInput | PumpEvaluationInput] = {}
        self._consumer_to_model_map: dict[tuple[UUID, Period], UUID] = {}
        self._ecalc_components: dict[UUID, EcalcComponent] = {}

    @property
    def evaluation_inputs(self) -> dict[UUID, CompressorEvaluationInput | PumpEvaluationInput]:
        return self._evaluation_inputs

    @property
    def process_systems(self) -> dict[UUID, CompressorTrainModel]:
        return self._process_systems

    @property
    def simplified_process_units(self) -> dict[UUID, CompressorModelSampled | PumpModel | CompressorWithTurbineModel]:
        return self._simplified_process_units

    @property
    def ecalc_components(self) -> dict[UUID, EcalcComponent]:
        return self._ecalc_components

    @property
    def consumer_to_model_map(self) -> dict[tuple[UUID, Period], UUID]:
        return self._consumer_to_model_map

    def register_process_system(
        self,
        ecalc_component: EcalcComponent,
        process_system: CompressorModel,
        evaluation_input: CompressorEvaluationInput,
    ):
        self._ecalc_components[ecalc_component.id] = ecalc_component
        self.process_systems[ecalc_component.id] = process_system
        self.evaluation_inputs[ecalc_component.id] = evaluation_input

    def register_simplified_process_unit(
        self,
        ecalc_component: EcalcComponent,
        simplified_process_unit: CompressorModelSampled | PumpModel | CompressorWithTurbineModel,
        evaluation_input: CompressorEvaluationInput | PumpEvaluationInput,
    ):
        self._ecalc_components[ecalc_component.id] = ecalc_component
        self.simplified_process_units[ecalc_component.id] = simplified_process_unit
        self.evaluation_inputs[ecalc_component.id] = evaluation_input

    def map_model_to_consumer(
        self,
        consumer_id: UUID,
        period: Period,
        ecalc_component: ProcessSystemComponent | SimplifiedProcessUnitComponent,
    ):
        self.consumer_to_model_map[(consumer_id, period)] = ecalc_component.id

    def get_evaluation_input(self, model_id: UUID) -> CompressorEvaluationInput | PumpEvaluationInput:
        return self.evaluation_inputs.get(model_id)
