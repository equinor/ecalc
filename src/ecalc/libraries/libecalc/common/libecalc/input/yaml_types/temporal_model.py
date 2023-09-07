from typing import MutableMapping, TypeVar, Union

from libecalc.input.yaml_types.variable import DefaultDatetime

TModel = TypeVar("TModel")
TemporalModel = Union[TModel, MutableMapping[DefaultDatetime, TModel]]
