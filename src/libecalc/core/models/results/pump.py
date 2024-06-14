from __future__ import annotations

from typing import List, Optional

from libecalc.core.models.results.base import EnergyFunctionResult
from libecalc.dto.types import PumpFailureStatus


class PumpModelResult(EnergyFunctionResult):
    rate: List[Optional[float]]
    suction_pressure: List[Optional[float]]
    discharge_pressure: List[Optional[float]]
    fluid_density: List[Optional[float]]
    operational_head: List[Optional[float]]
    failure_status: List[Optional[PumpFailureStatus]]

    @property
    def is_valid(self) -> List[bool]:
        failure_status_valid = [f == PumpFailureStatus.NO_FAILURE for f in self.failure_status]

        return failure_status_valid
