from pydantic import BaseModel, ConfigDict, field_validator

from libecalc.common.string.string_utils import to_camel_case
from libecalc.dto.utils.validators import EmissionNameStr, convert_expression
from libecalc.expression import Expression


class EcalcBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class Emission(EcalcBaseModel):
    name: EmissionNameStr
    factor: Expression  # Conversion factor for kg/day, i.e. fuel rate * factor -> kg/day

    _convert_expression = field_validator("factor", mode="before")(convert_expression)

    @field_validator("name", mode="before")
    @classmethod
    def convert_name(cls, name):
        return name.lower()
