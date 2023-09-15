from typing import Dict, TypeVar, Union

from libecalc.input.yaml_types.yaml_variable import YamlDefaultDatetime

TModel = TypeVar("TModel")
YamlTemporalModel = Union[TModel, Dict[YamlDefaultDatetime, TModel]]
