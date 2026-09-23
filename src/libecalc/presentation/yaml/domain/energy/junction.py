from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from libecalc.energy.dispatch import DispatchStrategy
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import Junction
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_energy
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(kw_only=True)
class TimeSeriesJunctionFactory(TimeSeriesEnergyUnitFactory):
    """Creates junctions with per-period input limits measured after upstream conversion and losses."""

    junction_class: type[Junction]
    dispatch_strategy: DispatchStrategy
    input_capacities: dict[EnergyUnitId, TimeSeriesExpression] = field(default_factory=dict)

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> Junction:
        energy_type = self.junction_class.get_energy_type()
        return self.junction_class(
            name=self.name,
            output_energy=demand,
            input_connection_ids={connection.source_id: connection.id for connection in incoming_connections},
            dispatch_strategy=self.dispatch_strategy,
            input_capacities={
                candidate_id: resolve_energy(
                    expression,
                    energy_type,
                    period=extra.get("period"),
                    description=f"Input capacity from {candidate_id} for '{self.name}'",
                )
                for candidate_id, expression in self.input_capacities.items()
            },
            energy_unit_id=self.energy_unit_id,
        )
