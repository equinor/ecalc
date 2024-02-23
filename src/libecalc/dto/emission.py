from pydantic import field_validator, validator

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.utils.validators import EmissionNameStr, convert_expression
from libecalc.expression import Expression


class Emission(EcalcBaseModel):
    name: EmissionNameStr
    factor: Expression  # Conversion factor for kg/day, i.e. fuel rate * factor -> kg/day

    _convert_expression = validator("factor", allow_reuse=True, pre=True)(convert_expression)

    @field_validator("name", mode="before")
    @classmethod
    def convert_name(cls, name):
        return name.lower()
