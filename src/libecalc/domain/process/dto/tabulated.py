from typing import Literal

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.exceptions import InvalidColumnException
from libecalc.domain.component_validation_error import (
    ModelValidationError,
    ProcessEqualLengthValidationException,
    ProcessHeaderValidationException,
)
from libecalc.domain.process.dto.sampled import EnergyModelSampled
from libecalc.presentation.yaml.validation_errors import Location


class TabulatedData(EnergyModelSampled):
    typ: Literal[EnergyModelType.TABULATED] = EnergyModelType.TABULATED

    def __init__(
        self,
        headers: list[str],
        data: list[list[float]],
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
    ):
        super().__init__(headers, data, energy_usage_adjustment_constant, energy_usage_adjustment_factor)
        self.validate_headers()
        self.validate_data()

    def get_energy_usage_type(self) -> EnergyUsageType:
        return EnergyUsageType.POWER if EnergyUsageType.POWER.value in self.headers else EnergyUsageType.FUEL

    def _get_function_value_header(self) -> str:
        return self.get_energy_usage_type().value

    def get_function_values(self) -> list[float]:
        return self.get_column(self._get_function_value_header())

    def get_variables(self) -> {str, list[float]}:
        variable_headers = [header for header in self.headers if header != self._get_function_value_header()]
        return {header: self.get_column(header) for header in variable_headers}

    def validate_headers(self):
        is_valid_headers = len(self.headers) > 0 and ("FUEL" in self.headers or "POWER" in self.headers)
        if not is_valid_headers:
            msg = "TABULAR facility input type data must have a 'FUEL' or 'POWER' header"

            raise ProcessHeaderValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

    def validate_data(self):
        lengths = [len(lst) for lst in self.data]
        if len(set(lengths)) > 1:
            problematic_vectors = [(i, len(lst)) for i, lst in enumerate(self.data)]
            msg = f"TABULAR facility input type data should have equal number of datapoints for all headers. Found lengths: {problematic_vectors}"

            raise ProcessEqualLengthValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )
        for column_index, header in enumerate(self.headers):
            for row_index, value in enumerate(self.data[column_index]):
                try:
                    float(value)
                except ValueError as e:
                    raise InvalidColumnException(
                        header=header, message=f"Got non-numeric value '{value}'.", row=row_index
                    ) from e
