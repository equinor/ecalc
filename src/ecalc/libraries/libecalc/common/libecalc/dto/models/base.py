from typing import Optional

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.types import ConsumerType, EnergyUsageType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from pydantic import validator


class ConsumerFunction(EcalcBaseModel):
    typ: ConsumerType
    energy_usage_type: EnergyUsageType
    condition: Optional[Expression]

    _convert_condition_to_expression = validator("condition", allow_reuse=True, pre=True)(convert_expression)

    class Config:
        use_enum_values = True


class EnergyModel(EcalcBaseModel):
    """Generic/template/protocol. Only for sub classing, not direct use."""

    energy_usage_adjustment_constant: float
    energy_usage_adjustment_factor: float

    class Config:
        use_enum_values = True
