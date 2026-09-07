import abc

from libecalc.energy.energy_types import ElectricalPower, Energy, FuelGasRate
from libecalc.energy.energy_unit import EnergyUnit


class Junction(EnergyUnit):
    """Aggregation point for energy of the same type.

    Connections and energy calculations are managed by EnergyNetwork.
    """

    @classmethod
    @abc.abstractmethod
    def get_energy_type(cls) -> type[Energy]: ...

    @classmethod
    def get_input_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()

    @classmethod
    def get_output_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()

    def get_input_energy(self, output_energy: Energy) -> Energy:
        """A junction aggregates without converting, so it draws exactly what it delivers."""
        return output_energy


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
