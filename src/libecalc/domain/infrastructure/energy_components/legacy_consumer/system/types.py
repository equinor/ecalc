from libecalc.domain.process.compressor.core.base import CompressorModel
from libecalc.domain.process.pump.pump_process_unit import PumpProcessUnit


class ConsumerSystemComponent:
    def __init__(self, name: str, facility_model: PumpProcessUnit | CompressorModel):
        self.name = name
        self.facility_model = facility_model
