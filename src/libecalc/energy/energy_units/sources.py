from libecalc.energy import Energy
from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.roles import Source


class FuelGasSource(Source):
    """Platform fuel gas supply, typically from the reservoir."""

    def __init__(self, name: str, max_rate: float | None = None, energy_unit_id: EnergyUnitId | None = None) -> None:
        super().__init__(name, energy_unit_id)
        self._max_rate = max_rate

    @classmethod
    def get_output_energy_type(cls) -> type[Energy]:
        return FuelGasRate

    def get_max_rate(self) -> float | None:
        return self._max_rate

    def capacity(self) -> FuelGasRate | None:
        return FuelGasRate(self._max_rate) if self._max_rate is not None else None


class OnshoreGrid(Source):
    """Onshore electrical grid connection, capped at contracted capacity."""

    def __init__(self, name: str, max_power: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        super().__init__(name, energy_unit_id)
        self._max_power = max_power

    @classmethod
    def get_output_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

    def get_max_power(self) -> float:
        return self._max_power

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self._max_power)


class OffshoreWind(Source):
    """Offshore wind park, capped at total rated output."""

    def __init__(self, name: str, power: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        super().__init__(name, energy_unit_id)
        self._power = power

    @classmethod
    def get_output_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

    def get_power(self) -> float:
        return self._power

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self._power)


class DieselSupply(Source):
    """Diesel fuel supply, brought to platform/rig by supply vessels."""

    def __init__(self, name: str, max_rate: float | None = None, energy_unit_id: EnergyUnitId | None = None) -> None:
        super().__init__(name, energy_unit_id)
        self._max_rate = max_rate

    @classmethod
    def get_output_energy_type(cls) -> type[DieselRate]:
        return DieselRate

    def get_max_rate(self) -> float | None:
        return self._max_rate

    def capacity(self) -> DieselRate | None:
        return DieselRate(self._max_rate) if self._max_rate is not None else None
