from typing import Any, Dict, List, Literal

from libecalc.dto.types import EnergyModelType
from pydantic import confloat, root_validator

from .base import EnergyModel


class Turbine(EnergyModel):
    typ: Literal[EnergyModelType.TURBINE] = EnergyModelType.TURBINE  # type: ignore
    lower_heating_value: confloat(ge=0)  # type: ignore
    turbine_loads: List[confloat(ge=0)]  # type: ignore
    turbine_efficiency_fractions: List[float]

    @root_validator
    def validate_loads_and_efficiency_factors(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        turbine_loads, turbine_efficiencies = (
            values["turbine_loads"],
            values["turbine_efficiency_fractions"],
        )
        if len(turbine_loads) != len(turbine_efficiencies):
            raise ValueError("Need equal number of load and efficiency values for turbine model")

        if not all(0 <= x <= 1 for x in turbine_efficiencies):
            raise ValueError("Turbine efficiency fraction should be a number between 0 and 1")
        return values
