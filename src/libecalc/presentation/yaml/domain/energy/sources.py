from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_units import DieselSource, ElectricalSource, FuelGasSource
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory


@dataclass(kw_only=True)
class TimeSeriesFuelGasSourceFactory(TimeSeriesEnergyUnitFactory):
    def create(self, demand: Energy, capacity: Energy | None, **extra: Any) -> FuelGasSource:
        return FuelGasSource(
            name=self.name,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            capacity=capacity,
        )


@dataclass(kw_only=True)
class TimeSeriesElectricalSourceFactory(TimeSeriesEnergyUnitFactory):
    def create(self, demand: Energy, capacity: Energy | None, **extra: Any) -> ElectricalSource:
        return ElectricalSource(
            name=self.name,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            capacity=capacity,
        )


@dataclass(kw_only=True)
class TimeSeriesDieselSourceFactory(TimeSeriesEnergyUnitFactory):
    def create(self, demand: Energy, capacity: Energy | None, **extra: Any) -> DieselSource:
        return DieselSource(
            name=self.name,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            capacity=capacity,
        )
