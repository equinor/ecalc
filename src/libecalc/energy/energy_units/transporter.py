import abc

from libecalc.energy import ElectricalPower, Energy, EnergyUnit, EnergyUnitId
from libecalc.energy.energy_failure import EnergyFailure, capacity_failures


class Transporter(EnergyUnit, abc.ABC):
    """Moves energy without changing form, possibly with loss.

    Subclasses set energy_type — input and output are always the same.
    """

    def __init__(
        self,
        name: str,
        output_energy: Energy,
        capacity: Energy | None = None,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name, energy_unit_id)
        self._output_energy = output_energy
        self._capacity = capacity

    def get_output_energy(self) -> Energy:
        return self._output_energy

    def get_capacity(self) -> Energy | None:
        return self._capacity

    def get_failures(self) -> list[EnergyFailure]:
        return capacity_failures(self._output_energy, self._capacity)

    @classmethod
    @abc.abstractmethod
    def get_energy_type(cls) -> type[Energy]: ...

    @classmethod
    def get_input_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()

    @classmethod
    def get_output_energy_type(cls) -> type[Energy]:
        return cls.get_energy_type()

    @abc.abstractmethod
    def get_input_energy(self) -> Energy:
        """Given output needed, what input is required?"""
        ...


class ElectricalCable(Transporter):
    """Electrical cable with transmission loss (e.g. subsea cable from shore)."""

    def __init__(
        self,
        name: str,
        output_energy: Energy,
        loss_fraction: float | None = None,
        capacity: Energy | None = None,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name, output_energy=output_energy, capacity=capacity, energy_unit_id=energy_unit_id)
        self._loss_fraction = loss_fraction if loss_fraction is not None else 0.0

    @classmethod
    def get_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

    def get_loss_fraction(self) -> float:
        return self._loss_fraction

    def get_input_energy(self) -> ElectricalPower:
        return ElectricalPower(self._output_energy.value / (1 - self._loss_fraction))
