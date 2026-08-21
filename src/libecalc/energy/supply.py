from __future__ import annotations

from dataclasses import dataclass

from libecalc.energy.demand import Demand


@dataclass(frozen=True)
class Supply[TDemand: Demand]:
    requested: TDemand
    delivered: TDemand
    input_consumed: Demand | None = None

    @property
    def unmet(self) -> TDemand | None:
        """Shortfall: requested - delivered. None if fully met."""
        if self.requested.value > self.delivered.value:
            return self.requested - self.delivered
        return None
