from libecalc.energy.energy_types import ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.roles import Junction


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


class Shaft(Junction):
    """Mechanical shaft: one driver, possibly many driven loads, with friction loss."""

    def __init__(self, name: str, loss_fraction: float = 0.0, energy_unit_id: EnergyUnitId | None = None) -> None:
        super().__init__(name, energy_unit_id, max_predecessors=1)
        self._loss_fraction = loss_fraction

    @classmethod
    def get_energy_type(cls) -> type[MechanicalPower]:
        return MechanicalPower

    def get_loss_fraction(self) -> float:
        return self._loss_fraction

    def _get_input_energy(self, output_energy: MechanicalPower) -> MechanicalPower:
        return MechanicalPower(output_energy.value / (1 - self._loss_fraction))
