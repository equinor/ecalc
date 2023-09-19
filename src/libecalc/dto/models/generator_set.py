from typing import List, Literal

from libecalc.dto.types import EnergyModelType
from pydantic.class_validators import validator

from .sampled import EnergyModelSampled


class GeneratorSetSampled(EnergyModelSampled):
    typ: Literal[EnergyModelType.GENERATOR_SET_SAMPLED] = EnergyModelType.GENERATOR_SET_SAMPLED

    @validator("headers")
    def validate_headers(cls, headers: List[str]) -> List[str]:
        is_valid_headers = len(headers) == 2 and "FUEL" in headers and "POWER" in headers
        if not is_valid_headers:
            raise ValueError("Sampled generator set data should have a 'FUEL' and 'POWER' header")
        return headers

    @validator("data")
    def validate_data(cls, data: List[List[float]]) -> List[List[float]]:
        if len({len(lst) for lst in data}) > 1:
            raise ValueError("Sampled generator set data should have equal number of datapoints for FUEL and POWER.")
        return data

    @property
    def fuel_values(self) -> List[float]:
        return self.data[self.headers.index("FUEL")]

    @property
    def power_values(self) -> List[float]:
        return self.data[self.headers.index("POWER")]
