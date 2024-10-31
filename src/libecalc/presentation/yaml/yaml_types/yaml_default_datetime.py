from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BeforeValidator, WithJsonSchema

from libecalc.common.time_utils import convert_date_to_datetime


def convert_str_or_date_to_datetime(x: Any):
    if isinstance(x, date):
        return convert_date_to_datetime(x)
    return x  # Let pydantic handle str and other types


YamlDefaultDatetime = Annotated[
    datetime,
    BeforeValidator(convert_str_or_date_to_datetime),
    WithJsonSchema({"type": "string", "format": "date"}),  # Previously just a str in the schema, is datetime needed?
]
