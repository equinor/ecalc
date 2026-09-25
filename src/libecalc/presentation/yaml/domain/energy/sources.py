from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.source import Source
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_optional_energy
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(kw_only=True)
class TimeSeriesSourceFactory(TimeSeriesEnergyUnitFactory):
    """Output energy type is carried by the `demand` value, so one class covers every source."""

    capacity: TimeSeriesExpression | None = None

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> Source:
        return Source(
            name=self.name,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            capacity=resolve_optional_energy(
                self.capacity,
                type(demand),
                period=extra.get("period"),
                description=f"Capacity for '{self.name}'",
            ),
        )
