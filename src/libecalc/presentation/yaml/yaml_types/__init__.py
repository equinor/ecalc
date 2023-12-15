from abc import ABC, abstractmethod

try:
    from pydantic.v1 import BaseModel, Extra
except ImportError:
    from pydantic import BaseModel, Extra


class YamlBase(BaseModel, ABC):
    class Config:
        allow_population_by_field_name = True
        alias_generator = str.upper
        extra = Extra.forbid
