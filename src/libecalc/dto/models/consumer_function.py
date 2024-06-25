from typing import Optional

from pydantic import ConfigDict, field_validator

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.types import ConsumerType, EnergyUsageType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression


class ConsumerFunction(EcalcBaseModel):
    typ: ConsumerType
    energy_usage_type: EnergyUsageType
    condition: Optional[Expression] = None

    _convert_condition_to_expression = field_validator("condition", mode="before")(convert_expression)
    model_config = ConfigDict(use_enum_values=True)
