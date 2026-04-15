from libecalc.domain.energy.drive_train.drive_train import DriveTrain, GeneratorSetDriveTrainResult
from libecalc.domain.energy.rotating_equipment.rotating_equipment import RotatingEquipment
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_model import GeneratorSetModel


class GeneratorSetDriveTrain(DriveTrain):
    """
    Electric motor driving rotating equipment via a shaft, powered by a fuel-burning generator set.

    required_electrical_power = shaft_power / mechanical_efficiency
    fuel = generator_set.evaluate_fuel_usage(required_electrical_power)
    """

    def __init__(
        self,
        generator_set: GeneratorSetModel,
        rotating_equipment: list[RotatingEquipment],
        mechanical_efficiency: float = 1.0,
    ):
        super().__init__(rotating_equipment=rotating_equipment, mechanical_efficiency=mechanical_efficiency)
        self._generator_set = generator_set

    def evaluate(self) -> GeneratorSetDriveTrainResult:
        shaft_power_mw = self.get_total_shaft_power_demand_mw()
        required_electrical_power_mw = self._required_power_mw()
        fuel_rate_sm3_per_day = self._generator_set.evaluate_fuel_usage(required_electrical_power_mw)
        power_capacity_margin_mw = self._generator_set.evaluate_power_capacity_margin(required_electrical_power_mw)
        return GeneratorSetDriveTrainResult(
            shaft_power_demand_mw=shaft_power_mw,
            required_electrical_power_mw=required_electrical_power_mw,
            fuel_rate_sm3_per_day=fuel_rate_sm3_per_day,
            power_capacity_margin_mw=power_capacity_margin_mw,
            exceeds_maximum_load=power_capacity_margin_mw < 0,
        )
