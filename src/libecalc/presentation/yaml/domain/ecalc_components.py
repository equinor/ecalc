from uuid import UUID

from libecalc.domain.ecalc_component import EcalcComponent


class CompressorProcessSystemComponent(EcalcComponent):
    def __init__(self, id: UUID, name: str, type: str):
        super().__init__(id=id, name=name, type=type)


class PumpProcessSystemComponent(EcalcComponent):
    def __init__(self, id: UUID, name: str, type: str):
        super().__init__(id=id, name=name, type=type)


class CompressorSampledComponent(EcalcComponent):
    def __init__(self, id: UUID, name: str, type: str):
        super().__init__(id=id, name=name, type=type)
