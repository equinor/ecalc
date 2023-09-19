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

    def for_timestep(self, timestep: datetime) -> EvaluatedPumpSystemOperationalSettings:
        """
        Get the operational settings evaluated across all consumers in the consumer system
        :param timestep:
        :return: A list of operational settings, the index in the list corresponds to the consumer index in the consumer system
        """
        new_rates = []
        new_inlet_pressures = []
        new_outlet_pressures = []
        new_crossover = []
        new_fluid_density = []
        for consumer_index, _ in enumerate(self.rates):
            new_rates.append(self.rates[consumer_index].for_timestep(timestep))
            new_inlet_pressures.append(self.inlet_pressures[consumer_index].for_timestep(timestep))
            new_outlet_pressures.append(self.outlet_pressures[consumer_index].for_timestep(timestep))
            new_fluid_density.append(self.fluid_density[consumer_index].for_timestep(timestep))
            new_crossover.append(self.crossover[consumer_index])

        return EvaluatedPumpSystemOperationalSettings(
            rates=new_rates,
            inlet_pressures=new_inlet_pressures,
            outlet_pressures=new_outlet_pressures,
            fluid_density=new_fluid_density,
            crossover=new_crossover,
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

    def for_timestep(self, timestep: datetime) -> EvaluatedCompressorSystemOperationalSettings:
        """
        Get the operational settings evaluated across all consumers in the consumer system
        :param timestep:
        :return: A list of operational settings, the index in the list corresponds to the consumer index in the consumer system
        """
        new_rates = []
        new_inlet_pressures = []
        new_outlet_pressures = []
        new_crossover = []
        for consumer_index, _ in enumerate(self.rates):
            new_rates.append(self.rates[consumer_index].for_timestep(timestep))
            new_inlet_pressures.append(self.inlet_pressures[consumer_index].for_timestep(timestep))
            new_outlet_pressures.append(self.outlet_pressures[consumer_index].for_timestep(timestep))
            new_crossover.append(self.crossover[consumer_index])

        return EvaluatedCompressorSystemOperationalSettings(
            rates=new_rates,
            inlet_pressures=new_inlet_pressures,
            outlet_pressures=new_outlet_pressures,
            crossover=new_crossover,
        )
