from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from libecalc.common.string.string_utils import to_camel_case


class EcalcResultBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )
