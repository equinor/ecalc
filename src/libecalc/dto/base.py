from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, ConfigDict

from libecalc.common.component_type import ComponentType
from libecalc.common.string.string_utils import to_camel_case


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
    def id(self) -> str: ...
