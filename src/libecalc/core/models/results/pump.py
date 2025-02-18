from __future__ import annotations

from enum import Enum
from typing import Optional

from libecalc.core.models.results.base import EnergyFunctionResult


class PumpFailureStatus(str, Enum):
    NO_FAILURE = "NO_FAILURE"
    ABOVE_MAXIMUM_PUMP_RATE = "ABOVE_MAXIMUM_PUMP_RATE"
    REQUIRED_HEAD_ABOVE_ACTUAL_HEAD = "REQUIRED_HEAD_ABOVE_ACTUAL_HEAD"
    ABOVE_MAXIMUM_HEAD_AT_RATE = "ABOVE_MAXIMUM_HEAD_AT_RATE"
    ABOVE_MAXIMUM_PUMP_RATE_AND_MAXIMUM_HEAD_AT_RATE = "ABOVE_MAXIMUM_PUMP_RATE_AND_MAXIMUM_HEAD_AT_RATE"


class PumpModelResult(EnergyFunctionResult):
    rate: list[Optional[float]]
    suction_pressure: list[Optional[float]]
    discharge_pressure: list[Optional[float]]
    fluid_density: list[Optional[float]]
    operational_head: list[Optional[float]]
    failure_status: list[Optional[PumpFailureStatus]]

    @property
    def is_valid(self) -> list[bool]:
        failure_status_valid = [f == PumpFailureStatus.NO_FAILURE for f in self.failure_status]

        return failure_status_valid
