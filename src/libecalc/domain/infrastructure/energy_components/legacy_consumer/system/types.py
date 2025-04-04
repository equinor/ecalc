from libecalc.domain.process.compressor.core.base import CompressorModel
from libecalc.domain.process.pump.pump import PumpModel


class ConsumerSystemComponent:
    def __init__(self, name: str, facility_model: PumpModel | CompressorModel):
        self.name = name
        self.facility_model = facility_model
