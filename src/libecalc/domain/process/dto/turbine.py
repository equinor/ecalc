from typing import Literal

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.domain.component_validation_error import (
    ModelValidationError,
    ProcessEqualLengthValidationException,
    ProcessTurbineEfficiencyValidationException,
)
from libecalc.domain.process.dto.base import EnergyModel
from libecalc.presentation.yaml.validation_errors import Location


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
            msg = (
                f"Need equal number of load and efficiency values for turbine model. "
                f"Got {len(self.turbine_loads)} load values and {len(self.turbine_efficiency_fractions)} efficiency values."
            )

            raise ProcessEqualLengthValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

        invalid_efficiencies = [x for x in self.turbine_efficiency_fractions if not 0 <= x <= 1]
        if invalid_efficiencies:
            msg = f"Turbine efficiency fraction should be a number between 0 and 1. Invalid values: {invalid_efficiencies}"

            raise ProcessTurbineEfficiencyValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )
