from enum import Enum


class ComponentType(str, Enum):
    ASSET = "ASSET"
    INSTALLATION = "INSTALLATION"
    GENERATOR_SET = "GENERATOR_SET"

    COMPRESSOR_SYSTEM = "COMPRESSOR_SYSTEM"
    PUMP_SYSTEM = "PUMP_SYSTEM"
    COMPRESSOR = "COMPRESSOR"
    PUMP = "PUMP"
    GENERIC = "GENERIC"
    VENTING_EMITTER = "VENTING_EMITTER"

    def __lt__(self, other: "ComponentType"):  # type: ignore[override]
        if self == other:
            return False
        # the following works because the order of elements in the definition is preserved
        for elem in ComponentType:
            if self == elem:
                return True
            elif other == elem:
                return False
