from __future__ import annotations

from enum import Enum

from libecalc.common.units import Unit
from libecalc.domain.process.core.results.base import EnergyFunctionResult


class PumpFailureStatus(str, Enum):
    NO_FAILURE = "NO_FAILURE"
    ABOVE_MAXIMUM_PUMP_RATE = "ABOVE_MAXIMUM_PUMP_RATE"
    REQUIRED_HEAD_ABOVE_ACTUAL_HEAD = "REQUIRED_HEAD_ABOVE_ACTUAL_HEAD"
    ABOVE_MAXIMUM_HEAD_AT_RATE = "ABOVE_MAXIMUM_HEAD_AT_RATE"
    ABOVE_MAXIMUM_PUMP_RATE_AND_MAXIMUM_HEAD_AT_RATE = "ABOVE_MAXIMUM_PUMP_RATE_AND_MAXIMUM_HEAD_AT_RATE"


class PumpModelResult(EnergyFunctionResult):
    def __init__(
        self,
        rate: list[float],
        suction_pressure: list[float],
        discharge_pressure: list[float],
        fluid_density: list[float],
        operational_head: list[float],
        failure_status: list[PumpFailureStatus],
        energy_usage: list[float],
        energy_usage_unit: Unit,
        power: list[float] | None,
        power_unit: Unit | None,
    ):
        super().__init__(
            energy_usage=energy_usage,
            energy_usage_unit=energy_usage_unit,
            power=power,
            power_unit=power_unit,
        )
        self.rate = rate
        self.suction_pressure = suction_pressure
        self.discharge_pressure = discharge_pressure
        self.fluid_density = fluid_density
        self.operational_head = operational_head
        self.failure_status = failure_status

    @property
    def is_valid(self) -> list[bool]:
        failure_status_valid = [f == PumpFailureStatus.NO_FAILURE for f in self.failure_status]

        return failure_status_valid
