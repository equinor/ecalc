from typing import Literal

from libecalc.common.consumer_type import ConsumerType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.utils.rates import RateType
from libecalc.domain.component_validation_error import (
    ModelValidationError,
    ProcessDirectConsumerFunctionValidationException,
)
from libecalc.domain.process.dto.base import ConsumerFunction
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from libecalc.presentation.yaml.validation_errors import Location


class DirectConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.DIRECT] = ConsumerType.DIRECT

    def __init__(
        self,
        energy_usage_type: EnergyUsageType,
        condition: Expression | None = None,
        fuel_rate: Expression | None = None,
        load: Expression | None = None,
        power_loss_factor: Expression | None = None,
        consumption_rate_type: RateType = RateType.STREAM_DAY,
    ):
        super().__init__(self.typ, energy_usage_type, condition)
        self.fuel_rate = convert_expression(fuel_rate)
        self.load = convert_expression(load)
        self.power_loss_factor = convert_expression(power_loss_factor)
        self.consumption_rate_type = consumption_rate_type
        self.validate_either_load_or_fuel_rate()

    def validate_either_load_or_fuel_rate(self):
        has_fuel_rate = self.fuel_rate is not None
        has_load = self.load is not None
        if not ((has_fuel_rate and not has_load) or (not has_fuel_rate and has_load)):
            msg = f"Either 'fuel_rate' or 'load' should be specified for '{ConsumerType.DIRECT}' models."

            raise ProcessDirectConsumerFunctionValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

    def __eq__(self, other):
        if not isinstance(other, DirectConsumerFunction):
            return False
        return (
            self.typ == other.typ
            and self.energy_usage_type == other.energy_usage_type
            and self.condition == other.condition
            and self.fuel_rate == other.fuel_rate
            and self.load == other.load
            and self.power_loss_factor == other.power_loss_factor
            and self.consumption_rate_type == other.consumption_rate_type
        )
