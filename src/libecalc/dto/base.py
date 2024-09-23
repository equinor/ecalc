from pydantic import BaseModel, ConfigDict

from libecalc.common.string.string_utils import to_camel_case


class EcalcBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )
