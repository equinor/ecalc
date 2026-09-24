from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from libecalc.common.time_utils import Period
from libecalc.energy import Energy
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnit
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(kw_only=True)
class TimeSeriesConsumer(TimeSeriesEnergyUnit):
    demand_for: Callable[[Period], Energy | None]

    def get_demand(self, period: Period) -> Energy | None:
        return self.demand_for(period)

    @classmethod
    def from_expression(
        cls, *, name: str, expression: TimeSeriesExpression | None, energy_type: type[Energy], **kwargs
    ) -> TimeSeriesConsumer:
        def demand(period: Period) -> Energy | None:
            if expression is None:
                return None
            return energy_type(value=expression.get_value(period))

        return cls(name=name, demand_for=demand, **kwargs)

    @classmethod
    def from_process_simulation(cls, *, name: str, energy_type: type[Energy], **kwargs) -> TimeSeriesConsumer:
        raise NotImplementedError("PROCESS_SIMULATION-driven demand is not supported yet")
