from typing import Union

from libecalc.domain.process.core.compressor.base import CompressorModel
from libecalc.domain.process.core.pump import PumpModel


class ConsumerSystemComponent:
    def __init__(self, name: str, facility_model: Union[PumpModel, CompressorModel]):
        self.name = name
        self.facility_model = facility_model
