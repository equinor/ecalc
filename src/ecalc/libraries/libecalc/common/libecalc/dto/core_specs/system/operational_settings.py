from __future__ import annotations

from datetime import datetime
from typing import List

from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesRate
from libecalc.dto.core_specs.compressor.operational_settings import (
    CompressorOperationalSettings,
)
from libecalc.dto.core_specs.pump.operational_settings import PumpOperationalSettings
from pydantic import BaseModel


class EvaluatedPumpSystemOperationalSettings(BaseModel):
    fluid_density: List[TimeSeriesFloat]
    rates: List[TimeSeriesRate]
    inlet_pressures: List[TimeSeriesFloat]
    outlet_pressures: List[TimeSeriesFloat]
    crossover: List[int]

    def get_consumer_operational_settings(
        self, consumer_index: int, timesteps: List[datetime]
    ) -> PumpOperationalSettings:
        return PumpOperationalSettings(
            stream_day_rates=[self.rates[consumer_index]],
            inlet_pressure=self.inlet_pressures[consumer_index],
            outlet_pressure=self.outlet_pressures[consumer_index],
            fluid_density=self.fluid_density[consumer_index],
            timesteps=timesteps,
        )


class EvaluatedCompressorSystemOperationalSettings(BaseModel):
    rates: List[TimeSeriesRate]
    inlet_pressures: List[TimeSeriesFloat]
    outlet_pressures: List[TimeSeriesFloat]
    crossover: List[int]

    def get_consumer_operational_settings(
        self, consumer_index: int, timesteps: List[datetime]
    ) -> CompressorOperationalSettings:
        return CompressorOperationalSettings(
            stream_day_rates=[self.rates[consumer_index]],
            inlet_pressure=self.inlet_pressures[consumer_index],
            outlet_pressure=self.outlet_pressures[consumer_index],
            timesteps=timesteps,
        )
