from __future__ import annotations

from collections.abc import Sequence

from libecalc.common.time_utils import Period
from libecalc.energy.energy_network_simulation import EnergyUnitFactory
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.energy.source import Source
from libecalc.presentation.yaml.domain.energy.base import ResolvedEnergyUnitFactory, TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_non_negative
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TimeSeriesSourceFactory(TimeSeriesEnergyUnitFactory):
    def __init__(
        self,
        *,
        name: str,
        energy_type: type[Energy],
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id, capacity=capacity)
        self.energy_type = energy_type

    def resolve(self, period: Period) -> EnergyUnitFactory:
        capacity = (
            resolve_non_negative(self.capacity, period=period, description=f"Capacity for '{self.get_name()}'")
            if self.capacity is not None
            else None
        )

        name, energy_unit_id, energy_type = self.get_name(), self.get_id(), self.energy_type

        def create(demand: Energy, incoming_connections: Sequence[EnergyConnection]) -> Source:
            if type(demand) is not energy_type:
                raise InvalidEnergyNetworkInputError(
                    f"Source '{name}' provides {energy_type.__name__}, got demand of {type(demand).__name__}"
                )
            return Source(
                name=name,
                energy_unit_id=energy_unit_id,
                output_energy=demand,
                capacity=energy_type(capacity) if capacity is not None else None,
            )

        return ResolvedEnergyUnitFactory(energy_unit_id=energy_unit_id, name=name, create=create)
