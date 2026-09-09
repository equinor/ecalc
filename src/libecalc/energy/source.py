from __future__ import annotations

import abc

from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit


class Source(EnergyUnit, abc.ABC):
    """Energy enters the system from an external source.

    Examples: power from shore (ElectricalPower), fuel gas supply (FuelGasRate).
    """

    @classmethod
    def get_input_energy_type(cls) -> None:
        return None

    @classmethod
    @abc.abstractmethod
    def get_output_energy_type(cls) -> type[Energy]: ...
