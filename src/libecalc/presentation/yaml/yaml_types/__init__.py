from abc import ABC

from pydantic import BaseModel, ConfigDict


class YamlBase(BaseModel, ABC):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=lambda field_name: field_name.upper(),
        extra="forbid",
    )
