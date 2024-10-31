from __future__ import annotations

from typing import Self

from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.time_utils import Period, Periods
from libecalc.dto.core_specs.base.operational_settings import OperationalSettings


class CompressorOperationalSettings(OperationalSettings):
    inlet_streams: list[TimeSeriesStreamConditions]
    outlet_stream: TimeSeriesStreamConditions

    periods: Periods

    def get_subset_for_period(self, current_period: Period) -> Self:
        """
        For a given timestep, get the operational settings that is relevant
        for that timestep only. Only valid for periods a part of the global periods.
        :param current_period: the period must be a part of the global periods
        :return:
        """

        return CompressorOperationalSettings(
            inlet_streams=[stream_condition.for_period(current_period) for stream_condition in self.inlet_streams],
            outlet_stream=self.outlet_stream.for_timestep(current_period),
            periods=[current_period],
        )
