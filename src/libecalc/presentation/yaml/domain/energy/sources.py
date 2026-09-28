from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_units import DieselSource, ElectricalSource, FuelGasSource
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_optional_energy


class TimeSeriesFuelGasSourceFactory(TimeSeriesEnergyUnitFactory):
    def create(
        self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any
    ) -> FuelGasSource:
        return FuelGasSource(
            name=self.get_name(),
            energy_unit_id=self.get_id(),
            output_energy=demand,
            capacity=resolve_optional_energy(
                self.capacity,
                FuelGasSource.get_output_energy_type(),
                period=extra.get("period"),
                description=f"Capacity for '{self.get_name()}'",
            ),
        )


class TimeSeriesElectricalSourceFactory(TimeSeriesEnergyUnitFactory):
    def create(
        self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any
    ) -> ElectricalSource:
        return ElectricalSource(
            name=self.get_name(),
            energy_unit_id=self.get_id(),
            output_energy=demand,
            capacity=resolve_optional_energy(
                self.capacity,
                ElectricalSource.get_output_energy_type(),
                period=extra.get("period"),
                description=f"Capacity for '{self.get_name()}'",
            ),
        )


class TimeSeriesDieselSourceFactory(TimeSeriesEnergyUnitFactory):
    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> DieselSource:
        return DieselSource(
            name=self.get_name(),
            energy_unit_id=self.get_id(),
            output_energy=demand,
            capacity=resolve_optional_energy(
                self.capacity,
                DieselSource.get_output_energy_type(),
                period=extra.get("period"),
                description=f"Capacity for '{self.get_name()}'",
            ),
        )
