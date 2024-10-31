from typing import Literal, Optional, Self

from pydantic import field_validator, model_validator

from libecalc.common.consumer_type import ConsumerType
from libecalc.common.utils.rates import RateType
from libecalc.dto.models.base import ConsumerFunction
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression


class DirectConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.DIRECT] = ConsumerType.DIRECT
    fuel_rate: Optional[Expression] = None
    load: Optional[Expression] = None
    power_loss_factor: Optional[Expression] = None
    consumption_rate_type: RateType = RateType.STREAM_DAY

    _convert_expressions = field_validator("fuel_rate", "load", "power_loss_factor", mode="before")(convert_expression)

    @model_validator(mode="after")
    def validate_either_load_or_fuel_rate(self) -> Self:
        has_fuel_rate = getattr(self, "fuel_rate", None) is not None
        has_load = getattr(self, "load", None) is not None
        if (has_fuel_rate and not has_load) or (not has_fuel_rate and has_load):
            return self
        raise ValueError(f"Either 'fuel_rate' or 'load' should be specified for '{ConsumerType.DIRECT}' models.")
