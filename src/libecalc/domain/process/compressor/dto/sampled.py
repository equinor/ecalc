from typing import Literal

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.domain.process.dto.base import EnergyModel


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
