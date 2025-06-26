from typing import Literal

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.domain.process.dto.sampled import EnergyModelSampled


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
