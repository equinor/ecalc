from abc import ABC

from pydantic import BaseModel, ConfigDict


class YamlBase(BaseModel, ABC):
    model_config = ConfigDict(populate_by_name=True, alias_generator=str.upper, extra="forbid")
