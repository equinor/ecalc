from enum import Enum


class ComponentType(str, Enum):
    ASSET = "ASSET"
    INSTALLATION = "INSTALLATION"
    GENERATOR_SET = "GENERATOR_SET"

    CONSUMER_SYSTEM_V2 = "CONSUMER_SYSTEM@v2"
    COMPRESSOR_SYSTEM = "COMPRESSOR_SYSTEM"
    PUMP_SYSTEM = "PUMP_SYSTEM"
    COMPRESSOR = "COMPRESSOR"
    COMPRESSOR_V2 = "COMPRESSOR@v2"
    PUMP = "PUMP"
    PUMP_V2 = "PUMP@v2"
    GENERIC = "GENERIC"
    # TURBINE = "TURBINE"
    VENTING_EMITTER = "VENTING_EMITTER"
    TRAIN_V2 = "TRAIN@V2"

    def __lt__(self, other: "ComponentType"):  # type: ignore[override]
        if self == other:
            return False
        # the following works because the order of elements in the definition is preserved
        for elem in ComponentType:
            if self == elem:
                return True
            elif other == elem:
                return False
