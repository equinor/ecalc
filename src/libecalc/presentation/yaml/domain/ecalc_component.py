from dataclasses import dataclass
from uuid import UUID

from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.evaluation_input import (
    CompressorEvaluationInput,
    CompressorSampledEvaluationInput,
    PumpEvaluationInput,
)
from libecalc.domain.process.pump.pump import PumpModel

ModelType = CompressorTrainModel | CompressorWithTurbineModel | CompressorModelSampled | PumpModel
EvalInputType = CompressorEvaluationInput | CompressorSampledEvaluationInput | PumpEvaluationInput


@dataclass
class EcalcComponent:
    id: UUID
    name: str
    type: str


@dataclass
class RegisteredComponent:
    ecalc_component: EcalcComponent
    model: ModelType
    evaluation_input: EvalInputType | None = None
    consumer_system_id: UUID | None = None
