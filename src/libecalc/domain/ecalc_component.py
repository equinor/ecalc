from uuid import UUID


class EcalcComponent:
    def __init__(self, id: UUID, name: str, type: str):
        self.id = id
        self.name = name
        self.type = type
