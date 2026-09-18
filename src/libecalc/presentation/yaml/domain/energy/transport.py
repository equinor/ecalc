from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from libecalc.common.time_utils import Period
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_units import ElectricalCable
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(kw_only=True)
class TimeSeriesElectricalCableFactory(TimeSeriesEnergyUnitFactory):
    loss_fraction: TimeSeriesExpression | None = None

    def create(self, demand: Energy, capacity: Energy | None, **extra: Any) -> ElectricalCable:
        period: Period = extra["period"]
        return ElectricalCable(
            name=self.name,
            loss_fraction=self.loss_fraction.get_value(period) if self.loss_fraction is not None else None,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            capacity=capacity,
        )
