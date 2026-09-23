from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from libecalc.common.time_utils import Period
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_units import ElectricalCable
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_optional_energy
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(kw_only=True)
class TimeSeriesElectricalCableFactory(TimeSeriesEnergyUnitFactory):
    capacity: TimeSeriesExpression | None = None
    loss_fraction: TimeSeriesExpression | None = None

    def create(
        self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any
    ) -> ElectricalCable:
        (incoming_connection,) = incoming_connections
        period: Period = extra["period"]
        return ElectricalCable(
            name=self.name,
            loss_fraction=self.loss_fraction.get_value(period) if self.loss_fraction is not None else None,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            capacity=resolve_optional_energy(
                self.capacity,
                ElectricalCable.get_output_energy_type(),
                period=extra.get("period"),
                description=f"Capacity for '{self.name}'",
            ),
        )
