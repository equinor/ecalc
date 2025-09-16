from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.dto.stage import CompressorStage
from libecalc.domain.process.dto.base import EnergyModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel


class CompressorTrain(EnergyModel):
    typ: EnergyModelType

    def __init__(
        self,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        typ: EnergyModelType,
        stages: list[CompressorStage],
        fluid_model: FluidModel | None = None,
        pressure_control: FixedSpeedPressureControl | None = None,
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
    ):
        super().__init__(energy_usage_adjustment_constant, energy_usage_adjustment_factor)
        self.typ = typ
        self.stages = stages
        self.fluid_model = fluid_model
        self.calculate_max_rate = calculate_max_rate
        self.maximum_power = maximum_power
        self.pressure_control = pressure_control
