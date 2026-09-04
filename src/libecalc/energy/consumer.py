from __future__ import annotations

import abc

from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit


class Consumer(EnergyUnit, abc.ABC):
    """Terminal energy unit representing an energy demand."""

    @classmethod
    @abc.abstractmethod
    def get_input_energy_type(cls) -> type[Energy]: ...

    @abc.abstractmethod
    def get_input_energy(self) -> Energy:
        """Return the input energy demanded by this consumer."""
        ...
