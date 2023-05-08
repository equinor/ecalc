from datetime import datetime
from typing import MutableMapping, TypeVar, Union

TModel = TypeVar("TModel")
TemporalModel = Union[TModel, MutableMapping[datetime, TModel]]
