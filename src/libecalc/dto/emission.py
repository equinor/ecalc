try:
    from pydantic.v1 import validator
except ImportError:
    from pydantic import validator

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.utils.validators import EmissionNameStr, convert_expression
from libecalc.expression import Expression


class Emission(EcalcBaseModel):
    name: EmissionNameStr
    factor: Expression  # Conversion factor for kg/day, i.e. fuel rate * factor -> kg/day

    _convert_expression = validator("factor", allow_reuse=True, pre=True)(convert_expression)

    @validator("name", pre=True)
    def convert_name(cls, name):
        return name.lower()
