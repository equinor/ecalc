from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from libecalc.common.units import Unit


class EnergyType(Enum):
    MECHANICAL = "MECHANICAL"
    ELECTRICAL = "ELECTRICAL"
    FUEL = "FUEL"


@dataclass(frozen=True)
class EnergyStream:
    """What flows between energy nodes."""

    energy_type: EnergyType
    value: float
    unit: Unit

    @staticmethod
    def mechanical(power_mw: float) -> EnergyStream:
        return EnergyStream(energy_type=EnergyType.MECHANICAL, value=power_mw, unit=Unit.MEGA_WATT)

    @staticmethod
    def electrical(power_mw: float) -> EnergyStream:
        return EnergyStream(energy_type=EnergyType.ELECTRICAL, value=power_mw, unit=Unit.MEGA_WATT)

    @staticmethod
    def fuel(rate_sm3_per_day: float) -> EnergyStream:
        return EnergyStream(energy_type=EnergyType.FUEL, value=rate_sm3_per_day, unit=Unit.STANDARD_CUBIC_METER_PER_DAY)
