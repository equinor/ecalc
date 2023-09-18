from typing import Any, Dict, Literal, Optional

from libecalc.dto.models.base import ConsumerFunction
from libecalc.dto.types import ConsumerType, RateType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from pydantic import root_validator, validator


class DirectConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.DIRECT] = ConsumerType.DIRECT
    fuel_rate: Optional[Expression]
    load: Optional[Expression]
    power_loss_factor: Optional[Expression] = None
    consumption_rate_type: RateType = RateType.STREAM_DAY

    _convert_expressions = validator("fuel_rate", "load", "power_loss_factor", allow_reuse=True, pre=True)(
        convert_expression
    )

    @root_validator
    def validate_either_load_or_fuel_rate(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values.get("fuel_rate") is None and values.get("load") is None:
            raise ValueError(f"Either 'fuel_rate' or 'load' should be specified for '{ConsumerType.DIRECT}' models.")
        return values
