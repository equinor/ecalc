from libecalc.energy import ElectricalPower, EnergyUnitId
from libecalc.energy.roles import Transporter


class ElectricalCable(Transporter):
    """Electrical cable with transmission loss (e.g. subsea cable from shore)."""

    def __init__(
        self, name: str, max_power: float, loss_fraction: float = 0.0, energy_unit_id: EnergyUnitId | None = None
    ) -> None:
        super().__init__(name, energy_unit_id)
        self._max_power = max_power
        self._loss_fraction = loss_fraction

    @classmethod
    def get_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

    def get_max_power(self) -> float:
        return self._max_power

    def get_loss_fraction(self) -> float:
        return self._loss_fraction

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self._max_power)

    def _get_input_energy(self, output_energy: ElectricalPower) -> ElectricalPower:
        return ElectricalPower(output_energy.value / (1 - self._loss_fraction))
