from typing import Dict, TypeVar, Union

from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlDefaultDatetime

TModel = TypeVar("TModel")
YamlTemporalModel = Union[TModel, Dict[YamlDefaultDatetime, TModel]]
# TODO: Make this a class, in order to easily add functionality such as yaml_temporal_model.get_model_at(timestep) ?
# How to do that in pydantic (v2)?
