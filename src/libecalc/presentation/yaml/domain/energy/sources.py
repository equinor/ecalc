from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.source import Source
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_optional_energy
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TimeSeriesSourceFactory(TimeSeriesEnergyUnitFactory):
    """Output energy type is carried by the `demand` value, so one class covers every source."""

    def __init__(
        self,
        *,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id, capacity=capacity)

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> Source:
        return Source(
            name=self.get_name(),
            energy_unit_id=self.get_id(),
            output_energy=demand,
            capacity=resolve_optional_energy(
                self.capacity,
                type(demand),
                period=extra.get("period"),
                description=f"Capacity for '{self.get_name()}'",
            ),
        )
