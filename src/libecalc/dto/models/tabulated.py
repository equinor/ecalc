from typing import List, Literal, Optional

from pydantic import field_validator

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.models.base import ConsumerFunction
from libecalc.dto.models.sampled import EnergyModelSampled
from libecalc.dto.types import ConsumerType, EnergyModelType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression


class TabulatedData(EnergyModelSampled):
    typ: Literal[EnergyModelType.TABULATED] = EnergyModelType.TABULATED

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, headers: List[str]) -> List[str]:
        is_valid_headers = len(headers) > 0 and "FUEL" in headers or "POWER" in headers
        if not is_valid_headers:
            raise ValueError("TABULAR facility input type data must have a 'FUEL' or 'POWER' header")
        return headers


class Variables(EcalcBaseModel):
    name: str
    expression: Expression

    _convert_variable_expression = field_validator("expression", mode="before")(convert_expression)


class TabulatedConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.TABULATED] = ConsumerType.TABULATED
    power_loss_factor: Optional[Expression] = None
    model: TabulatedData
    variables: List[Variables]

    _convert_to_expression = field_validator("power_loss_factor", mode="before")(convert_expression)
