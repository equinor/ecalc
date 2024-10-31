from typing import Literal

from pydantic import field_validator

from ...common.energy_model_type import EnergyModelType
from .sampled import EnergyModelSampled


class GeneratorSetSampled(EnergyModelSampled):
    typ: Literal[EnergyModelType.GENERATOR_SET_SAMPLED] = EnergyModelType.GENERATOR_SET_SAMPLED

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, headers: list[str]) -> list[str]:
        is_valid_headers = len(headers) == 2 and "FUEL" in headers and "POWER" in headers
        if not is_valid_headers:
            raise ValueError("Sampled generator set data should have a 'FUEL' and 'POWER' header")
        return headers

    @field_validator("data")
    @classmethod
    def validate_data(cls, data: list[list[float]]) -> list[list[float]]:
        if len({len(lst) for lst in data}) > 1:
            raise ValueError("Sampled generator set data should have equal number of datapoints for FUEL and POWER.")
        return data

    @property
    def fuel_values(self) -> list[float]:
        return self.data[self.headers.index("FUEL")]

    @property
    def power_values(self) -> list[float]:
        return self.data[self.headers.index("POWER")]
