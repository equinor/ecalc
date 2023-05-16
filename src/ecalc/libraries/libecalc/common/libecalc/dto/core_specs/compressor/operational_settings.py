from __future__ import annotations

from datetime import datetime
from typing import List

from libecalc.common.time_utils import Period
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesRate
from libecalc.dto.core_specs.base.operational_settings import OperationalSettings
from typing_extensions import Self


class CompressorOperationalSettings(OperationalSettings):
    """Todo: Create abstract baseclass: OperationalSettingsBase handling CONDITION, POWERLOSSFACTOR, etc."""

    stream_day_rates: List[TimeSeriesRate]
    inlet_pressure: TimeSeriesFloat
    outlet_pressure: TimeSeriesFloat
    timesteps: List[datetime]

    def get_subset_from_period(self, period: Period) -> Self:
        start_index, end_index = period.get_timestep_indices(self.timesteps)

        return CompressorOperationalSettings(
            stream_day_rates=[rate[start_index:end_index] for rate in self.stream_day_rates],
            inlet_pressure=self.inlet_pressure[start_index:end_index],
            outlet_pressure=self.outlet_pressure[start_index:end_index],
            timesteps=self.timesteps[start_index:end_index],
        )

    @property
    def regularity(self) -> List[float]:
        return self.stream_day_rates[0].regularity
