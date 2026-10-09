from __future__ import annotations

from collections.abc import Sequence

from libecalc.common.time_utils import Period
from libecalc.energy.energy_network_simulation import EnergyUnitFactory
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import ElectricalCable
from libecalc.presentation.yaml.domain.energy.base import ResolvedEnergyUnitFactory, TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import (
    resolve_optional_energy,
    resolve_optional_loss_fraction,
)
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TimeSeriesElectricalCableFactory(TimeSeriesEnergyUnitFactory):
    def __init__(
        self,
        *,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
        loss_fraction: TimeSeriesExpression | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id, capacity=capacity)
        self.loss_fraction = loss_fraction

    def resolve(self, period: Period) -> EnergyUnitFactory:
        loss_fraction = resolve_optional_loss_fraction(
            self.loss_fraction, period=period, description=f"Loss fraction for '{self.get_name()}'"
        )
        capacity = resolve_optional_energy(
            self.capacity,
            ElectricalCable.get_output_energy_type(),
            period=period,
            description=f"Capacity for '{self.get_name()}'",
        )

        name, energy_unit_id = self.get_name(), self.get_id()

        def create(demand: Energy, incoming_connections: Sequence[EnergyConnection]) -> ElectricalCable:
            (incoming_connection,) = incoming_connections
            return ElectricalCable(
                name=name,
                loss_fraction=loss_fraction,
                energy_unit_id=energy_unit_id,
                output_energy=demand,
                input_connection_id=incoming_connection.id,
                capacity=capacity,
            )

        return ResolvedEnergyUnitFactory(energy_unit_id=energy_unit_id, name=name, create=create)
