import numpy as np

from libecalc.domain.energy.drive_train.drive_train import DriveTrain, TurbineDriveTrainResult
from libecalc.domain.energy.rotating_equipment.rotating_equipment import RotatingEquipment
from libecalc.domain.infrastructure.energy_components.turbine.turbine import Turbine


class TurbineDriveTrain(DriveTrain):
    """
    Gas turbine driving rotating equipment via a shaft.

    required_mechanical_power = shaft_power / mechanical_efficiency
    fuel = turbine.evaluate(required_mechanical_power)
    """

    def __init__(
        self,
        turbine: Turbine,
        rotating_equipment: list[RotatingEquipment],
        mechanical_efficiency: float = 1.0,
    ):
        super().__init__(rotating_equipment=rotating_equipment, mechanical_efficiency=mechanical_efficiency)
        self._turbine = turbine

    def evaluate(self) -> TurbineDriveTrainResult:
        shaft_power_mw = self.get_total_shaft_power_demand_mw()

        required_mechanical_power_mw = self._required_power_mw()
        # Turbine.evaluate() takes/returns arrays (legacy). We pass a single value.
        result = self._turbine.evaluate(load=np.array([required_mechanical_power_mw]))
        energy_result = result.get_energy_result()
        return TurbineDriveTrainResult(
            shaft_power_demand_mw=shaft_power_mw,
            required_mechanical_power_mw=required_mechanical_power_mw,
            fuel_rate_sm3_per_day=energy_result.energy_usage.values[0],
            exceeds_maximum_load=result.exceeds_maximum_load[0],
        )
