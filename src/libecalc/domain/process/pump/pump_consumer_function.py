from typing import Literal

from libecalc.common.consumer_type import ConsumerType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.domain.process.dto.base import ConsumerFunction
from libecalc.domain.process.pump.pump import PumpModelDTO
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression


class PumpConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.PUMP] = ConsumerType.PUMP
    energy_usage_type: EnergyUsageType = EnergyUsageType.POWER

    def __init__(
        self,
        model: PumpModelDTO,
        rate_standard_m3_day: Expression,
        suction_pressure: Expression,
        discharge_pressure: Expression,
        fluid_density: Expression,
        power_loss_factor: Expression | None = None,
        condition: Expression | None = None,
    ):
        super().__init__(typ=self.typ, energy_usage_type=self.energy_usage_type, condition=condition)
        self.model = model
        self.rate_standard_m3_day = convert_expression(rate_standard_m3_day)
        self.suction_pressure = convert_expression(suction_pressure)
        self.discharge_pressure = convert_expression(discharge_pressure)
        self.fluid_density = convert_expression(fluid_density)
        self.power_loss_factor = convert_expression(power_loss_factor)
