from __future__ import annotations

import abc

from libecalc.energy.demand import Demand
from libecalc.energy.energy_unit import EnergyUnit


class Consumer[TDemand: Demand](EnergyUnit, abc.ABC):
    """Demands energy. End of the energy chain.

    Examples: compressor (mechanical), pump (mechanical),
              base load (electrical), flare (fuel).
    """

    @abc.abstractmethod
    def get_demand(self) -> TDemand: ...
