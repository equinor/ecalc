from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_units import DieselSource, ElectricalSource, FuelGasSource
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_optional_energy
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(kw_only=True)
class TimeSeriesFuelGasSourceFactory(TimeSeriesEnergyUnitFactory):
    capacity: TimeSeriesExpression | None = None

    def create(
        self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any
    ) -> FuelGasSource:
        return FuelGasSource(
            name=self.name,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            capacity=resolve_optional_energy(
                self.capacity,
                FuelGasSource.get_output_energy_type(),
                period=extra.get("period"),
                description=f"Capacity for '{self.name}'",
            ),
        )


@dataclass(kw_only=True)
class TimeSeriesElectricalSourceFactory(TimeSeriesEnergyUnitFactory):
    capacity: TimeSeriesExpression | None = None

    def create(
        self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any
    ) -> ElectricalSource:
        return ElectricalSource(
            name=self.name,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            capacity=resolve_optional_energy(
                self.capacity,
                ElectricalSource.get_output_energy_type(),
                period=extra.get("period"),
                description=f"Capacity for '{self.name}'",
            ),
        )


@dataclass(kw_only=True)
class TimeSeriesDieselSourceFactory(TimeSeriesEnergyUnitFactory):
    capacity: TimeSeriesExpression | None = None

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> DieselSource:
        return DieselSource(
            name=self.name,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            capacity=resolve_optional_energy(
                self.capacity,
                DieselSource.get_output_energy_type(),
                period=extra.get("period"),
                description=f"Capacity for '{self.name}'",
            ),
        )
