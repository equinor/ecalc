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
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor
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
        evaluation_input: CompressorEvaluationInput,
    ): ...

    @abstractmethod
    def register_pump_process_system(
        self,
        ecalc_component: EcalcComponent,
        pump_process_system: PumpModel,
        evaluation_input: PumpEvaluationInput,
    ): ...

    @abstractmethod
    def register_compressor_sampled(
        self,
        ecalc_component: EcalcComponent,
        compressor_sampled: CompressorModelSampled | CompressorWithTurbineModel,
        evaluation_input: CompressorSampledEvaluationInput,
    ): ...

    @abstractmethod
    def register_consumer_system(
        self,
        system_id: UUID,
        component_ids: list[UUID],
        consumer_id: UUID,
        power_loss_factor: TimeSeriesPowerLossFactor,
    ): ...

    @abstractmethod
    def map_model_to_consumer(
        self,
        consumer_id: UUID,
        period: Period,
        ecalc_component: CompressorProcessSystemComponent | PumpProcessSystemComponent | CompressorSampledComponent,
    ): ...
