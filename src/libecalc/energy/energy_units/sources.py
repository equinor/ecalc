from typing import Final

from libecalc.energy.demand import DieselRate, ElectricalPower, FuelGasRate
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.provider import Source


class FuelGasSource(Source[FuelGasRate]):
    """Platform fuel gas supply, typically from the reservoir."""

    def __init__(self, name: str, max_rate: float | None = None, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._max_rate = max_rate
        self._id: Final[EnergyUnitId] = energy_unit_id or FuelGasSource._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_max_rate(self) -> float | None:
        return self._max_rate

    def capacity(self) -> FuelGasRate | None:
        return FuelGasRate(self._max_rate) if self._max_rate is not None else None


class OnshoreGrid(Source[ElectricalPower]):
    """Onshore electrical grid connection, capped at contracted capacity."""

    def __init__(self, name: str, max_power: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._max_power = max_power
        self._id: Final[EnergyUnitId] = energy_unit_id or OnshoreGrid._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_max_power(self) -> float:
        return self._max_power

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self._max_power)


class OffshoreWind(Source[ElectricalPower]):
    """Offshore wind park, capped at total rated output."""

    def __init__(self, name: str, power: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._power = power
        self._id: Final[EnergyUnitId] = energy_unit_id or OffshoreWind._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_power(self) -> float:
        return self._power

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self._power)


class DieselSupply(Source[DieselRate]):
    """Diesel fuel supply, brought to platform/rig by supply vessels."""

    def __init__(self, name: str, max_rate: float | None = None, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._max_rate = max_rate
        self._id: Final[EnergyUnitId] = energy_unit_id or DieselSupply._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_max_rate(self) -> float | None:
        return self._max_rate

    def capacity(self) -> DieselRate | None:
        return DieselRate(self._max_rate) if self._max_rate is not None else None
