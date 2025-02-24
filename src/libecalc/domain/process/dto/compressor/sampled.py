from typing import Annotated, Literal, Optional

from pydantic import Field, model_validator

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.domain.process.dto.base import EnergyModel


class CompressorSampled(EnergyModel):
    typ: Literal[EnergyModelType.COMPRESSOR_SAMPLED] = EnergyModelType.COMPRESSOR_SAMPLED
    energy_usage_type: EnergyUsageType
    energy_usage_values: list[Annotated[float, Field(ge=0)]]
    rate_values: Optional[list[Annotated[float, Field(ge=0)]]] = None
    suction_pressure_values: Optional[list[Annotated[float, Field(ge=0)]]] = None
    discharge_pressure_values: Optional[list[Annotated[float, Field(ge=0)]]] = None
    power_interpolation_values: Optional[list[Annotated[float, Field(ge=0)]]] = None

    # skip_on_failure required if not pre=True, we don't need validation of lengths if other validations fails
    @model_validator(mode="after")
    def validate_equal_list_lengths(self):
        number_of_data_points = len(self.energy_usage_values)
        for variable_name in (
            "rate_values",
            "suction_pressure_values",
            "discharge_pressure_values",
            "power_interpolation_values",
        ):
            variable = getattr(self, variable_name)
            if variable is not None:
                if len(variable) != number_of_data_points:
                    raise ValueError(
                        f"{variable_name} has wrong number of points. "
                        f"Should have {number_of_data_points} (equal to number of energy usage value points)"
                    )
        return self

    @model_validator(mode="before")
    def validate_minimum_one_variable(cls, values):
        rate_not_given = "rate_values" not in values
        suction_pressure_not_given = "suction_pressure_values" not in values
        discharge_pressure_not_given = "discharge_pressure_values" not in values
        if rate_not_given and suction_pressure_not_given and discharge_pressure_not_given:
            raise ValueError(
                "Need at least one variable for CompressorTrainSampled (rate, suction_pressure or discharge_pressure)"
            )
        return values
