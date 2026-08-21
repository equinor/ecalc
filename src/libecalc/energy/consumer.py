from __future__ import annotations

import abc

from libecalc.energy.demand import Demand


class Consumer[TDemand: Demand](abc.ABC):
    """Demands energy. End of the energy chain.

    Examples: compressor (mechanical), pump (mechanical),
              base load (electrical), flare (fuel).
    """

    @abc.abstractmethod
    def get_id(self) -> str: ...

    @abc.abstractmethod
    def get_demand(self) -> TDemand: ...
