from __future__ import annotations

from libecalc.energy.dispatch import DispatchStrategy
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TimeSeriesJunctionFactory(TimeSeriesEnergyUnitFactory):
    """Junction configuration with per-period input limits measured after upstream conversion and losses."""

    def __init__(
        self,
        *,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
        energy_type: type[Energy],
        dispatch_strategy: DispatchStrategy,
        input_capacities: dict[EnergyUnitId, TimeSeriesExpression] | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.energy_type = energy_type
        self.dispatch_strategy = dispatch_strategy
        self.input_capacities = input_capacities or {}
