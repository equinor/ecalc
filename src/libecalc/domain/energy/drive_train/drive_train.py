from abc import ABC, abstractmethod
from dataclasses import dataclass

from libecalc.domain.energy.rotating_equipment.rotating_equipment import RotatingEquipment


@dataclass
class DriveTrainResult:
    shaft_power_demand_mw: float
    fuel_rate_sm3_per_day: float
    exceeds_maximum_load: bool


@dataclass
class TurbineDriveTrainResult(DriveTrainResult):
    required_mechanical_power_mw: float = 0.0


@dataclass
class GeneratorSetDriveTrainResult(DriveTrainResult):
    required_electrical_power_mw: float = 0.0
    power_capacity_margin_mw: float = 0.0


class DriveTrain(ABC):
    """
    A driver (gas turbine or electric motor) that supplies mechanical power
    to rotating equipment.

    Sums shaft power demand from all connected rotating equipment,
    accounts for mechanical losses, and calculates required fuel consumption.

    Note: The physical shaft and speed control live in the process domain.
    DriveTrain only sees the resulting power demand.
    """

    def __init__(
        self,
        rotating_equipment: list[RotatingEquipment],
        mechanical_efficiency: float = 1.0,
    ):
        self._rotating_equipment = rotating_equipment
        self._mechanical_efficiency = mechanical_efficiency

    @property
    def mechanical_efficiency(self) -> float:
        return self._mechanical_efficiency

    def get_total_shaft_power_demand_mw(self) -> float:
        return sum(r.get_shaft_power_demand_mw() for r in self._rotating_equipment)

    def _required_power_mw(self) -> float:
        """What the driver must produce, accounting for mechanical losses."""
        return self.get_total_shaft_power_demand_mw() / self._mechanical_efficiency

    @abstractmethod
    def evaluate(self) -> DriveTrainResult: ...
