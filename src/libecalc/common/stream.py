from typing import Literal

from libecalc.common.string_utils import to_camel_case
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesStreamDayRate
from pydantic import BaseModel, Extra


class Stream(BaseModel):
    class Config:
        extra = Extra.forbid
        alias_generator = to_camel_case
        allow_population_by_field_name = True

    rate: TimeSeriesStreamDayRate
    pressure: TimeSeriesFloat
    fluid_density: TimeSeriesFloat = None


class Stage(BaseModel):
    class Config:
        extra = Extra.forbid
        alias_generator = to_camel_case
        allow_population_by_field_name = True

    name: Literal["inlet", "before_choke", "outlet"]
    stream: Stream
