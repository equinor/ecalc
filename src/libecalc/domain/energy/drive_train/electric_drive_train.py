from dataclasses import dataclass

from libecalc.domain.energy.drive_train.drive_train import DriveTrain, DriveTrainResult


@dataclass
class ElectricDriveTrainResult(DriveTrainResult):
    """Electric motor — only knows how much electrical power it needs."""

    required_electrical_power_mw: float


class ElectricDriveTrain(DriveTrain):
    """
    Electric motor driving rotating equipment via a shaft.

    Computes the electrical power demand needed to deliver the total shaft power,
    accounting for mechanical losses. Does not know where the electricity comes from —
    that's the responsibility of a PowerSupply.
    """

    def evaluate(self) -> ElectricDriveTrainResult:
        shaft_power = self.get_total_shaft_power_demand_mw()
        required_electrical_power = self._required_power_mw()

        return ElectricDriveTrainResult(
            shaft_power_demand_mw=shaft_power,
            required_electrical_power_mw=required_electrical_power,
        )
