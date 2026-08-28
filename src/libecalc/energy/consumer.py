from __future__ import annotations

import abc

from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit


class Consumer(EnergyUnit, abc.ABC):
    """Demands energy. End of the energy chain.

    Examples: compressor (mechanical), pump (mechanical),
              base load (electrical), flare (fuel).
    """

    @classmethod
    @abc.abstractmethod
    def get_input_energy_type(cls) -> type[Energy]: ...

    @abc.abstractmethod
    def get_input_energy(self) -> Energy: ...
