from typing import List, Literal

from pydantic import Field, model_validator
from typing_extensions import Annotated, Self

from libecalc.dto.types import EnergyModelType

from .base import EnergyModel


class Turbine(EnergyModel):
    typ: Literal[EnergyModelType.TURBINE] = EnergyModelType.TURBINE  # type: ignore
    lower_heating_value: Annotated[float, Field(ge=0)]
    turbine_loads: List[Annotated[float, Field(ge=0)]]
    turbine_efficiency_fractions: List[float]

    @model_validator(mode="after")
    def validate_loads_and_efficiency_factors(self) -> Self:
        turbine_loads, turbine_efficiencies = (
            self.turbine_loads,
            self.turbine_efficiency_fractions,
        )
        if len(turbine_loads) != len(turbine_efficiencies):
            raise ValueError("Need equal number of load and efficiency values for turbine model")

        if not all(0 <= x <= 1 for x in turbine_efficiencies):
            raise ValueError("Turbine efficiency fraction should be a number between 0 and 1")
        return self
