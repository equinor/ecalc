from typing import Literal, Optional

from pydantic import field_validator

from libecalc.common.consumer_type import ConsumerType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.domain.process.dto.base import ConsumerFunction
from libecalc.domain.process.pump.pump import PumpModelDTO
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression


class PumpConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.PUMP] = ConsumerType.PUMP
    energy_usage_type: EnergyUsageType = EnergyUsageType.POWER
    power_loss_factor: Optional[Expression] = None
    model: PumpModelDTO
    rate_standard_m3_day: Expression
    suction_pressure: Expression
    discharge_pressure: Expression
    fluid_density: Expression

    _convert_pump_expressions = field_validator(
        "rate_standard_m3_day",
        "suction_pressure",
        "discharge_pressure",
        "fluid_density",
        "power_loss_factor",
        mode="before",
    )(convert_expression)
