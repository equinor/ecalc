from abc import ABC, abstractmethod
from uuid import UUID

from libecalc.common.time_utils import Period
from libecalc.domain.ecalc_component import EcalcComponent
from libecalc.domain.process.compressor.core.base import CompressorModel, CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.evaluation_input import CompressorEvaluationInput, PumpEvaluationInput
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.presentation.yaml.domain.ecalc_components import ProcessSystemComponent, SimplifiedProcessUnitComponent


class ProcessService(ABC):
    @abstractmethod
    def register_process_system(
        self,
        ecalc_component: EcalcComponent,
        process_system: CompressorModel,
        evaluation_input: CompressorEvaluationInput,
    ): ...

    @abstractmethod
    def register_simplified_process_unit(
        self,
        ecalc_component: EcalcComponent,
        simplified_process_unit: CompressorModelSampled | PumpModel | CompressorWithTurbineModel,
        evaluation_input: CompressorEvaluationInput | PumpEvaluationInput,
    ): ...

    @abstractmethod
    def map_model_to_consumer(
        self,
        consumer_id: UUID,
        period: Period,
        ecalc_component: ProcessSystemComponent | SimplifiedProcessUnitComponent,
    ): ...

    @abstractmethod
    def get_evaluation_input(self, process_system_id: UUID) -> CompressorEvaluationInput | PumpEvaluationInput: ...
