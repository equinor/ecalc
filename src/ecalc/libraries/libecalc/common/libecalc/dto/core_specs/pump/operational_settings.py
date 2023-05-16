from __future__ import annotations

from datetime import datetime
from typing import List

from libecalc.common.time_utils import Period
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesRate
from libecalc.dto.core_specs.base.operational_settings import OperationalSettings
from typing_extensions import Self


class PumpOperationalSettings(OperationalSettings):
    stream_day_rates: List[TimeSeriesRate]
    inlet_pressure: TimeSeriesFloat
    outlet_pressure: TimeSeriesFloat
    fluid_density: TimeSeriesFloat
    timesteps: List[datetime]

    def get_subset_from_period(self, period: Period) -> Self:
        start_index, end_index = period.get_timestep_indices(self.timesteps)

        return PumpOperationalSettings(
            stream_day_rates=[rate[start_index:end_index] for rate in self.stream_day_rates],
            inlet_pressure=self.inlet_pressure[start_index:end_index],
            outlet_pressure=self.outlet_pressure[start_index:end_index],
            fluid_density=self.fluid_density[start_index:end_index],
            timesteps=self.timesteps[start_index:end_index],
        )
