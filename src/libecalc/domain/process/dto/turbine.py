from typing import Literal

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.domain.process.dto.base import EnergyModel


class Turbine(EnergyModel):
    typ: Literal[EnergyModelType.TURBINE] = EnergyModelType.TURBINE

    def __init__(
        self,
        lower_heating_value: float,
        turbine_loads: list[float],
        turbine_efficiency_fractions: list[float],
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
    ):
        super().__init__(energy_usage_adjustment_constant, energy_usage_adjustment_factor)
        self.lower_heating_value = lower_heating_value
        self.turbine_loads = turbine_loads
        self.turbine_efficiency_fractions = turbine_efficiency_fractions
        self.validate_loads_and_efficiency_factors()

    def validate_loads_and_efficiency_factors(self):
        if len(self.turbine_loads) != len(self.turbine_efficiency_fractions):
            raise ValueError("Need equal number of load and efficiency values for turbine model")

        if not all(0 <= x <= 1 for x in self.turbine_efficiency_fractions):
            raise ValueError("Turbine efficiency fraction should be a number between 0 and 1")
