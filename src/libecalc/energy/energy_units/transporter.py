import abc

from libecalc.energy import ElectricalPower, Energy, EnergyUnit, EnergyUnitId


class Transporter(EnergyUnit, abc.ABC):
    """Moves energy without changing form, possibly with loss.

    Subclasses set energy_type — input and output are always the same.
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

    @abc.abstractmethod
    def get_input_energy(self, output_energy: Energy) -> Energy:
        """Given output needed, what input is required?"""
        ...


class ElectricalCable(Transporter):
    """Electrical cable with transmission loss (e.g. subsea cable from shore)."""

    def __init__(
        self,
        name: str,
        loss_fraction: float | None = None,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name, energy_unit_id)
        self._loss_fraction = loss_fraction if loss_fraction is not None else 0.0

    @classmethod
    def get_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

    def get_loss_fraction(self) -> float:
        return self._loss_fraction

    def get_input_energy(self, output_energy: ElectricalPower) -> ElectricalPower:
        return ElectricalPower(output_energy.value / (1 - self._loss_fraction))
