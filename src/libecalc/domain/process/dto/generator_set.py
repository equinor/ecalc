from typing import Literal

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.presentation.yaml.validation_errors import Location

from ...component_validation_error import (
    ModelValidationError,
    ProcessEqualLengthValidationException,
    ProcessHeaderValidationException,
)
from .sampled import EnergyModelSampled


class GeneratorSetSampled(EnergyModelSampled):
    typ: Literal[EnergyModelType.GENERATOR_SET_SAMPLED] = EnergyModelType.GENERATOR_SET_SAMPLED

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

    def validate_headers(self):
        is_valid_headers = len(self.headers) == 2 and "FUEL" in self.headers and "POWER" in self.headers
        if not is_valid_headers:
            msg = "Sampled generator set data should have a 'FUEL' and 'POWER' header"

            raise ProcessHeaderValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

    def validate_data(self):
        lengths = [len(lst) for lst in self.data]
        if len(set(lengths)) > 1:
            problematic_vectors = [(i, len(lst)) for i, lst in enumerate(self.data)]
            msg = f"Sampled generator set data should have equal number of datapoints for FUEL and POWER. Found lengths: {problematic_vectors}"

            raise ProcessEqualLengthValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

    @property
    def fuel_values(self) -> list[float]:
        return self.data[self.headers.index("FUEL")]

    @property
    def power_values(self) -> list[float]:
        return self.data[self.headers.index("POWER")]

    def __eq__(self, other):
        if not isinstance(other, GeneratorSetSampled):
            return False
        return (
            self.typ == other.typ
            and self.headers == other.headers
            and self.data == other.data
            and self.energy_usage_adjustment_constant == other.energy_usage_adjustment_constant
            and self.energy_usage_adjustment_factor == other.energy_usage_adjustment_factor
        )
