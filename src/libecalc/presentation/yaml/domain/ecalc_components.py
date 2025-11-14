from uuid import UUID

from libecalc.domain.ecalc_component import EcalcComponent


class ProcessSystemComponent(EcalcComponent):
    def __init__(self, id: UUID, name: str, type: str):
        super().__init__(id=id, name=name, type=type)


class SimplifiedProcessUnitComponent(EcalcComponent):
    def __init__(self, id: UUID, name: str, type: str):
        super().__init__(id=id, name=name, type=type)
