import abc
from typing import Final

from libecalc.energy.energy_types import ElectricalPower, Energy, FuelGasRate
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId


class Junction(EnergyUnit):
    """Aggregation point for energy of the same type.

    Connections to providers and consumers are managed by the Network,
    not by internal lists. The solver resolves capacity and demand
    from the network graph.
    """

    def __init__(self, name: str, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._id: Final[EnergyUnitId] = energy_unit_id or Junction._create_id()

    @classmethod
    @abc.abstractmethod
    def get_energy_type(cls) -> type[Energy]: ...

    @classmethod
    def get_input_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()

    @classmethod
    def get_output_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name


class ElectricalBus(Junction):
    """Electrical power distribution bus (busbar)."""

    @classmethod
    def get_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower


class FuelGasManifold(Junction):
    """Fuel gas distribution manifold (header)."""

    @classmethod
    def get_energy_type(cls) -> type[FuelGasRate]:
        return FuelGasRate
