from abc import abstractmethod
from datetime import datetime
from functools import partial
from typing import List, Optional, Protocol

from orjson import orjson
from pydantic import BaseModel, Extra
from pydantic.json import custom_pydantic_encoder

from libecalc.common.string.string_utils import to_camel_case
from libecalc.core.consumers.base.component import ConsumerID
from libecalc.domain.stream_conditions import Rate, StreamConditions


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


class ModelResult(Protocol):
    @abstractmethod
    @property
    def streams(self) -> List[StreamConditions]:
        ...


class ConsumerResult(EcalcBaseModel):
    """Base component for all results: Model, Installation, GenSet, Consumer System, Consumer, etc."""

    id: ConsumerID
    timestep: datetime
    is_valid: bool

    # We need both energy usage and power rate since we sometimes want both fuel and power usage.
    energy_usage: Rate
    power: Optional[Rate]
    streams: List[StreamConditions]

    @abstractmethod
    @property
    def models(self) -> List[ModelResult]:
        ...
