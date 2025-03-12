from libecalc.common.consumer_type import ConsumerType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression


class ConsumerFunction:
    def __init__(self, typ: ConsumerType, energy_usage_type: EnergyUsageType, condition: Expression | None = None):
        self.typ = typ
        self.energy_usage_type = energy_usage_type
        self.condition = convert_expression(condition)


class EnergyModel:
    """Generic/template/protocol. Only for sub classing, not direct use."""

    def __init__(self, energy_usage_adjustment_constant: float, energy_usage_adjustment_factor: float):
        self.energy_usage_adjustment_constant = energy_usage_adjustment_constant
        self.energy_usage_adjustment_factor = energy_usage_adjustment_factor
