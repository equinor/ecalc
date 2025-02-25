from typing import Optional

from pydantic import ConfigDict, field_validator

from libecalc.common.consumer_type import ConsumerType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression


class ConsumerFunction(EcalcBaseModel):
    typ: ConsumerType
    energy_usage_type: EnergyUsageType
    condition: Optional[Expression] = None

    _convert_condition_to_expression = field_validator("condition", mode="before")(convert_expression)
    model_config = ConfigDict(use_enum_values=True)


class EnergyModel(EcalcBaseModel):
    """Generic/template/protocol. Only for sub classing, not direct use."""

    energy_usage_adjustment_constant: float
    energy_usage_adjustment_factor: float
    model_config = ConfigDict(use_enum_values=True)
