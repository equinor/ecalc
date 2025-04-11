from typing import Literal

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.domain.process.dto.sampled import EnergyModelSampled
from libecalc.domain.process.generator_set.generator_set_validator import GeneratorSetSampledValidator


class GeneratorSetData(EnergyModelSampled):
    typ: Literal[EnergyModelType.GENERATOR_SET_SAMPLED] = EnergyModelType.GENERATOR_SET_SAMPLED

    def __init__(
        self,
        headers: list[str],
        data: list[list[float]],
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
    ):
        self.validator = GeneratorSetSampledValidator(headers, data, self.typ.value)
        super().__init__(headers, data, energy_usage_adjustment_constant, energy_usage_adjustment_factor)

    def validate_headers(self):
        self.validator.validate_headers()

    def validate_data(self):
        self.validator.validate_data()

    @property
    def fuel_values(self) -> list[float]:
        return self.data[self.headers.index("FUEL")]

    @property
    def power_values(self) -> list[float]:
        return self.data[self.headers.index("POWER")]

    def __eq__(self, other):
        if not isinstance(other, GeneratorSetData):
            return False
        return (
            self.typ == other.typ
            and self.headers == other.headers
            and self.data == other.data
            and self.energy_usage_adjustment_constant == other.energy_usage_adjustment_constant
            and self.energy_usage_adjustment_factor == other.energy_usage_adjustment_factor
        )
