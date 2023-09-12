from typing import Dict, TypeVar, Union

from pydantic import ConstrainedStr


class DatetimeString(ConstrainedStr):
    regex = "^\\d{4}\\-(0?[1-9]|1[012])\\-(0?[1-9]|[12][0-9]|3[01])$"


TModel = TypeVar("TModel")
TemporalModel = Union[TModel, Dict[DatetimeString, TModel]]
