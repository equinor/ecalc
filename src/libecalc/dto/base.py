from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, ConfigDict

from libecalc.common.string.string_utils import to_camel_case


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


class ConsumerUserDefinedCategoryType(str, Enum):
    """
    Consumer category
    """

    BASE_LOAD = "BASE-LOAD"
    COLD_VENTING_FUGITIVE = "COLD-VENTING-FUGITIVE"
    COMPRESSOR = "COMPRESSOR"
    FIXED_PRODUCTION_LOAD = "FIXED-PRODUCTION-LOAD"
    FLARE = "FLARE"
    MISCELLANEOUS = "MISCELLANEOUS"
    PUMP = "PUMP"
    GAS_DRIVEN_COMPRESSOR = "GAS-DRIVEN-COMPRESSOR"
    TURBINE_GENERATOR = "TURBINE-GENERATOR"
    POWER_FROM_SHORE = "POWER-FROM-SHORE"
    OFFSHORE_WIND = "OFFSHORE-WIND"
    LOADING = "LOADING"
    STORAGE = "STORAGE"
    STEAM_TURBINE_GENERATOR = "STEAM-TURBINE-GENERATOR"
    BOILER = "BOILER"
    HEATER = "HEATER"


class InstallationUserDefinedCategoryType(str, Enum):
    """
    Installation category
    """

    FIXED = "FIXED"
    MOBILE = "MOBILE"


class FuelTypeUserDefinedCategoryType(str, Enum):
    FUEL_GAS = "FUEL-GAS"
    DIESEL = "DIESEL"


class EcalcBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class Component(EcalcBaseModel, ABC):
    component_type: ComponentType

    @property
    @abstractmethod
    def id(self) -> str:
        ...
