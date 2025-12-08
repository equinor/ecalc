from abc import ABC, abstractmethod
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
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.presentation.yaml.domain.ecalc_components import (
    CompressorProcessSystemComponent,
    CompressorSampledComponent,
    PumpProcessSystemComponent,
)


class ProcessService(ABC):
    @abstractmethod
    def register_compressor_process_system(
        self,
        ecalc_component: EcalcComponent,
        compressor_process_system: CompressorTrainModel | CompressorWithTurbineModel,
    ): ...

    @abstractmethod
    def register_pump_process_system(
        self,
        ecalc_component: EcalcComponent,
        pump_process_system: PumpModel,
    ): ...

    @abstractmethod
    def register_compressor_sampled(
        self,
        ecalc_component: EcalcComponent,
        compressor_sampled: CompressorModelSampled | CompressorWithTurbineModel,
    ): ...

    @abstractmethod
    def register_evaluation_input(
        self,
        ecalc_component: EcalcComponent,
        evaluation_input: CompressorEvaluationInput | CompressorSampledEvaluationInput | PumpEvaluationInput,
    ): ...

    @abstractmethod
    def map_model_to_consumer(
        self,
        consumer_id: UUID,
        period: Period,
        ecalc_component: CompressorProcessSystemComponent | PumpProcessSystemComponent | CompressorSampledComponent,
    ): ...

    @abstractmethod
    def get_evaluation_input(
        self, process_system_id: UUID
    ) -> CompressorEvaluationInput | CompressorSampledEvaluationInput | PumpEvaluationInput: ...
