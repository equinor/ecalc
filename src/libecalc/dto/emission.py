from typing import Optional

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.utils.validators import EmissionNameStr, convert_expression
from libecalc.expression import Expression
from pydantic import validator


class Emission(EcalcBaseModel):
    """As with fuel, the predictive models of cost and fees for emissions will change."""

    name: EmissionNameStr
    factor: Expression  # Conversion factor for kg/day, i.e. fuel rate * factor -> kg/day
    tax: Optional[Expression]
    quota: Optional[Expression]

    _convert_expression = validator("factor", "tax", "quota", allow_reuse=True, pre=True)(convert_expression)

    @validator("name", pre=True)
    def convert_name(cls, name):
        return name.lower()
