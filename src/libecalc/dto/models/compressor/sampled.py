from typing import List, Literal, Optional

from libecalc.dto.models.base import EnergyModel
from libecalc.dto.types import EnergyModelType, EnergyUsageType
from pydantic import confloat
from pydantic.class_validators import root_validator


class CompressorSampled(EnergyModel):
    typ: Literal[EnergyModelType.COMPRESSOR_SAMPLED] = EnergyModelType.COMPRESSOR_SAMPLED
    energy_usage_type: EnergyUsageType
    energy_usage_values: List[confloat(ge=0)]
    rate_values: Optional[List[confloat(ge=0)]]
    suction_pressure_values: Optional[List[confloat(ge=0)]]
    discharge_pressure_values: Optional[List[confloat(ge=0)]]
    power_interpolation_values: Optional[List[confloat(ge=0)]]

    @root_validator
    def validate_equal_list_lengths(cls, values):
        number_of_data_points = len(values["energy_usage_values"])
        for variable_name in (
            "rate_values",
            "suction_pressure_values",
            "discharge_pressure_values",
            "power_interpolation_values",
        ):
            variable = values.get(variable_name)
            if variable is not None:
                if len(variable) != number_of_data_points:
                    raise ValueError(
                        f"{variable_name} has wrong number of points. "
                        f"Should have {number_of_data_points} (equal to number of energy usage value points)"
                    )
        return values

    @root_validator(pre=True)
    def validate_minimum_one_variable(cls, values):
        rate_not_given = "rate_values" not in values
        suction_pressure_not_given = "suction_pressure_values" not in values
        discharge_pressure_not_given = "discharge_pressure_values" not in values
        if rate_not_given and suction_pressure_not_given and discharge_pressure_not_given:
            raise ValueError(
                "Need at least one variable for CompressorTrainSampled (rate, suction_pressure or discharge_pressure)"
            )
        return values
