from __future__ import annotations

from datetime import datetime
from typing import List

from libecalc.common.stream import Stream
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesStreamDayRate
from libecalc.dto.core_specs.compressor.operational_settings import (
    CompressorOperationalSettings,
)
from libecalc.dto.core_specs.pump.operational_settings import PumpOperationalSettings
from pydantic import BaseModel


class EvaluatedPumpSystemOperationalSettings(BaseModel):
    fluid_density: List[TimeSeriesFloat]
    rates: List[TimeSeriesStreamDayRate]
    inlet_pressures: List[TimeSeriesFloat]
    outlet_pressures: List[TimeSeriesFloat]

    def get_consumer_operational_settings(
        self, consumer_index: int, timesteps: List[datetime]
    ) -> PumpOperationalSettings:
        inlet_stream = Stream(
            rate=self.rates[consumer_index],
            pressure=self.inlet_pressures[consumer_index],
            fluid_density=self.fluid_density[consumer_index],
        )
        return PumpOperationalSettings(
            inlet_streams=[inlet_stream],
            outlet_stream=Stream(
                rate=inlet_stream.rate,
                pressure=self.outlet_pressures[consumer_index],
                fluid_density=inlet_stream.fluid_density,
            ),
            timesteps=timesteps,
        )

    def for_timestep(self, timestep: datetime) -> EvaluatedPumpSystemOperationalSettings:
        """
        Get the operational settings evaluated across all consumers in the consumer system
        :param timestep:
        :return: A list of operational settings, the index in the list corresponds to the consumer index in the consumer system
        """
        new_rates = []
        new_inlet_pressures = []
        new_outlet_pressures = []
        new_fluid_density = []
        for consumer_index, _ in enumerate(self.rates):
            new_rates.append(self.rates[consumer_index].for_timestep(timestep))
            new_inlet_pressures.append(self.inlet_pressures[consumer_index].for_timestep(timestep))
            new_outlet_pressures.append(self.outlet_pressures[consumer_index].for_timestep(timestep))
            new_fluid_density.append(self.fluid_density[consumer_index].for_timestep(timestep))

        return EvaluatedPumpSystemOperationalSettings(
            rates=new_rates,
            inlet_pressures=new_inlet_pressures,
            outlet_pressures=new_outlet_pressures,
            fluid_density=new_fluid_density,
        )


class EvaluatedCompressorSystemOperationalSettings(BaseModel):
    rates: List[TimeSeriesStreamDayRate]
    inlet_pressures: List[TimeSeriesFloat]
    outlet_pressures: List[TimeSeriesFloat]

    def get_consumer_operational_settings(
        self, consumer_index: int, timesteps: List[datetime]
    ) -> CompressorOperationalSettings:
        inlet_stream = Stream(
            rate=self.rates[consumer_index],
            pressure=self.inlet_pressures[consumer_index],
        )
        return CompressorOperationalSettings(
            inlet_streams=[inlet_stream],
            outlet_stream=Stream(
                rate=inlet_stream.rate,
                pressure=self.outlet_pressures[consumer_index],
            ),
            timesteps=timesteps,
        )

    def for_timestep(self, timestep: datetime) -> EvaluatedCompressorSystemOperationalSettings:
        """
        Get the operational settings evaluated across all consumers in the consumer system
        :param timestep:
        :return: A list of operational settings, the index in the list corresponds to the consumer index in the consumer system
        """
        new_rates = []
        new_inlet_pressures = []
        new_outlet_pressures = []
        for consumer_index, _ in enumerate(self.rates):
            new_rates.append(self.rates[consumer_index].for_timestep(timestep))
            new_inlet_pressures.append(self.inlet_pressures[consumer_index].for_timestep(timestep))
            new_outlet_pressures.append(self.outlet_pressures[consumer_index].for_timestep(timestep))

        return EvaluatedCompressorSystemOperationalSettings(
            rates=new_rates,
            inlet_pressures=new_inlet_pressures,
            outlet_pressures=new_outlet_pressures,
        )
