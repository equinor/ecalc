from typing import Final

from libecalc.energy.demand import Demand, ElectricalPower, FuelGasRate
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId


class Junction[T: Demand](EnergyUnit):
    """Aggregation point for energy of the same type.

    Connections to providers and consumers are managed by the Network,
    not by internal lists. The solver resolves capacity and demand
    from the network graph.
    """

    def __init__(self, name: str, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._id: Final[EnergyUnitId] = energy_unit_id or Junction._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name


class ElectricalBus(Junction[ElectricalPower]):
    """Electrical power distribution bus (busbar)."""

    ...


class FuelGasManifold(Junction[FuelGasRate]):
    """Fuel gas distribution manifold (header)."""

    ...
