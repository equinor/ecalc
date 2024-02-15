from typing import Literal, Optional, Union

from pydantic import field_validator

from libecalc.dto.models.base import ConsumerFunction, EnergyModel
from libecalc.dto.models.chart import SingleSpeedChart, VariableSpeedChart
from libecalc.dto.types import ConsumerType, EnergyModelType, EnergyUsageType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression


class PumpModel(EnergyModel):
    typ: Literal[EnergyModelType.PUMP_MODEL] = EnergyModelType.PUMP_MODEL
    chart: Union[SingleSpeedChart, VariableSpeedChart]
    head_margin: float


class PumpConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.PUMP] = ConsumerType.PUMP
    energy_usage_type: EnergyUsageType = EnergyUsageType.POWER
    power_loss_factor: Optional[Expression] = None
    model: PumpModel
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
