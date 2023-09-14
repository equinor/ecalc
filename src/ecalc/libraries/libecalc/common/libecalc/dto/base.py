from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from functools import partial
from typing import Optional

from libecalc.common.string_utils import to_camel_case
from libecalc.expression import Expression
from orjson import orjson
from pydantic import BaseModel, Extra
from pydantic.json import custom_pydantic_encoder


class ComponentType(str, Enum):
    ASSET = "ASSET"
    INSTALLATION = "INSTALLATION"
    GENERATOR_SET = "GENERATOR_SET"

    COMPRESSOR_SYSTEM_V2 = "COMPRESSOR_SYSTEM@v2"
    COMPRESSOR_SYSTEM = "COMPRESSOR_SYSTEM"
    PUMP_SYSTEM_V2 = "PUMP_SYSTEM@v2"
    PUMP_SYSTEM = "PUMP_SYSTEM"
    COMPRESSOR = "COMPRESSOR"
    PUMP = "PUMP"
    GENERIC = "GENERIC"
    # TURBINE = "TURBINE"
    DIRECT_EMITTER = "DIRECT_EMITTER"

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


def orjson_dumps(v, *, default, indent: bool = False):
    options = orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_PASSTHROUGH_DATETIME

    if indent:
        options = options | orjson.OPT_INDENT_2

    # orjson.dumps returns bytes, to match standard json.dumps we need to decode
    # default is the pydantic json encoder
    return orjson.dumps(v, default=default, option=options).decode("utf-8")


class EcalcBaseModel(BaseModel):
    class Config:
        extra = Extra.forbid
        alias_generator = to_camel_case
        allow_population_by_field_name = True
        json_dumps = orjson_dumps
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M:%S"),
            Expression: lambda e: str(e),
        }
        copy_on_model_validation = "deep"

    def json(self, date_format: Optional[str] = None, **kwargs) -> str:
        if date_format is None:
            return super().json(**kwargs)

        if kwargs.get("encoder") is None:
            # Override datetime encoder if not already overridden, use user specified date_format_option
            encoder = partial(
                custom_pydantic_encoder,
                {
                    datetime: lambda v: v.strftime(date_format),
                },
            )
        else:
            encoder = kwargs["encoder"]

        return super().json(**kwargs, encoder=encoder)  # Encoder becomes default, i.e. should handle unhandled types


class Component(EcalcBaseModel, ABC):
    component_type: ComponentType

    @property
    @abstractmethod
    def id(self) -> str:
        ...
