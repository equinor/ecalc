from typing import Literal

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import InvalidColumnException
from libecalc.domain.component_validation_error import (
    ModelValidationError,
    ProcessEqualLengthValidationException,
    ProcessMissingVariableValidationException,
    ProcessNegativeValuesValidationException,
)
from libecalc.domain.process.dto.base import EnergyModel
from libecalc.presentation.yaml.validation_errors import Location


class CompressorSampled(EnergyModel):
    typ: Literal[EnergyModelType.COMPRESSOR_SAMPLED] = EnergyModelType.COMPRESSOR_SAMPLED

    def __init__(
        self,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        energy_usage_type: EnergyUsageType,
        energy_usage_values: list[float],
        rate_values: list[float] | None = None,
        suction_pressure_values: list[float] | None = None,
        discharge_pressure_values: list[float] | None = None,
        power_interpolation_values: list[float] | None = None,
    ):
        super().__init__(energy_usage_adjustment_constant, energy_usage_adjustment_factor)
        self.energy_usage_type = energy_usage_type
        self.energy_usage_values = energy_usage_values
        self.rate_values = rate_values
        self.suction_pressure_values = suction_pressure_values
        self.discharge_pressure_values = discharge_pressure_values
        self.power_interpolation_values = power_interpolation_values

        self.validate_minimum_one_variable()
        self.validate_equal_list_lengths()
        self.validate_non_negative_values()

    # skip_on_failure required if not pre=True, we don't need validation of lengths if other validations fails
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
                    msg = (
                        f"{variable_name} has wrong number of points. "
                        f"Should have {number_of_data_points} (equal to number of energy usage value points)"
                    )

                    raise ProcessEqualLengthValidationException(
                        errors=[
                            ModelValidationError(
                                name=variable_name, location=Location([variable_name]), message=str(msg)
                            )
                        ],
                    )

    def validate_minimum_one_variable(self):
        if not self.rate_values and not self.suction_pressure_values and not self.discharge_pressure_values:
            msg = "Need at least one variable for CompressorTrainSampled (rate, suction_pressure or discharge_pressure)"

            raise ProcessMissingVariableValidationException(
                errors=[
                    ModelValidationError(
                        name="CompressorTrainSampled",
                        location=Location(["CompressorTrainSampled"]),  # for now, we will use the name as the location
                        message=str(msg),
                    )
                ],
            )

    def validate_non_negative_values(self):
        for variable_name in (
            "energy_usage_values",
            "rate_values",
            "suction_pressure_values",
            "discharge_pressure_values",
            "power_interpolation_values",
        ):
            variable = getattr(self, variable_name)
            if variable is not None:
                for i, value in enumerate(variable):
                    try:
                        float(value)
                    except ValueError as e:
                        raise InvalidColumnException(
                            header=variable_name, message=f"Got non-numeric value '{value}'.", row=i
                        ) from e

                if any(value < 0 for value in variable):
                    msg = f"All values in {variable_name} must be greater than or equal to 0"

                    raise ProcessNegativeValuesValidationException(
                        errors=[
                            ModelValidationError(
                                name=variable_name,
                                location=Location([variable_name]),  # for now, we will use the name as the location
                                message=str(msg),
                            )
                        ],
                    )
