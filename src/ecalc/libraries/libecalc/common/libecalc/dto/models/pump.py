from typing import Literal, Optional, Union

from libecalc.dto.models.base import ConsumerFunction, EnergyModel
from libecalc.dto.models.chart import SingleSpeedChart, VariableSpeedChart
from libecalc.dto.types import ConsumerType, EnergyModelType, EnergyUsageType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from pydantic import validator


class PumpModel(EnergyModel):
    typ: Literal[EnergyModelType.PUMP_MODEL] = EnergyModelType.PUMP_MODEL
    chart: Union[SingleSpeedChart, VariableSpeedChart]
    head_margin: float


class PumpConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.PUMP] = ConsumerType.PUMP
    energy_usage_type = EnergyUsageType.POWER
    power_loss_factor: Optional[Expression]
    model: PumpModel
    rate_standard_m3_day: Expression
    suction_pressure: Expression
    discharge_pressure: Expression
    fluid_density: Expression

    _convert_pump_expressions = validator(
        "rate_standard_m3_day",
        "suction_pressure",
        "discharge_pressure",
        "fluid_density",
        "power_loss_factor",
        allow_reuse=True,
        pre=True,
    )(convert_expression)
