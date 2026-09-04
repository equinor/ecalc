from libecalc.energy.consumer import Consumer
from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId


class ElectricalConsumer(Consumer):
    """Consumes electrical power."""

    def __init__(self, name: str, power: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        super().__init__(name, energy_unit_id)
        self._power = power

    @classmethod
    def get_input_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

    def get_power(self) -> float:
        return self._power

    def get_input_energy(self) -> ElectricalPower:
        return ElectricalPower(self._power)


class MechanicalConsumer(Consumer):
    """Consumes mechanical power."""

    def __init__(self, name: str, power: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        super().__init__(name, energy_unit_id)
        self._power = power

    @classmethod
    def get_input_energy_type(cls) -> type[MechanicalPower]:
        return MechanicalPower

    def get_power(self) -> float:
        return self._power

    def get_input_energy(self) -> MechanicalPower:
        return MechanicalPower(self._power)


class FuelGasConsumer(Consumer):
    """Consumes fuel gas."""

    def __init__(self, name: str, rate: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        super().__init__(name, energy_unit_id)
        self._rate = rate

    @classmethod
    def get_input_energy_type(cls) -> type[FuelGasRate]:
        return FuelGasRate

    def get_rate(self) -> float:
        return self._rate

    def get_input_energy(self) -> FuelGasRate:
        return FuelGasRate(self._rate)


class DieselConsumer(Consumer):
    """Consumes diesel."""

    def __init__(self, name: str, rate: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        super().__init__(name, energy_unit_id)
        self._rate = rate

    @classmethod
    def get_input_energy_type(cls) -> type[DieselRate]:
        return DieselRate

    def get_rate(self) -> float:
        return self._rate

    def get_input_energy(self) -> DieselRate:
        return DieselRate(self._rate)
