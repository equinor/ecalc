from __future__ import annotations

from datetime import datetime
from typing import List

from typing_extensions import Self

from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.dto.core_specs.base.operational_settings import OperationalSettings


class PumpOperationalSettings(OperationalSettings):
    inlet_streams: List[TimeSeriesStreamConditions]
    outlet_stream: TimeSeriesStreamConditions

    timesteps: List[datetime]

    def get_subset_for_timestep(self, current_timestep: datetime) -> Self:
        """
        For a given timestep, get the operational settings that is relevant
        for that timestep only. Only valid for timesteps a part of the global timevector.
        :param current_timestep: the timestep must be a part of the global timevector
        :return:
        """

        return PumpOperationalSettings(
            inlet_streams=[stream_condition.for_timestep(current_timestep) for stream_condition in self.inlet_streams],
            outlet_stream=self.outlet_stream.for_timestep(current_timestep),
            timesteps=[current_timestep],
        )
