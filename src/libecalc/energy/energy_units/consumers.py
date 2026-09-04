from typing import Final

from libecalc.energy.consumer import Consumer
from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId


class ElectricalConsumer(Consumer):
    def __init__(self, name: str, load: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._load = load
        self._id: Final[EnergyUnitId] = energy_unit_id or ElectricalConsumer._create_id()

    @classmethod
    def get_input_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_load(self) -> float:
        return self._load

    def get_input_energy(self) -> ElectricalPower:
        return ElectricalPower(self._load)


class FuelGasConsumer(Consumer):
    def __init__(self, name: str, rate: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._rate = rate
        self._id: Final[EnergyUnitId] = energy_unit_id or FuelGasConsumer._create_id()

    @classmethod
    def get_input_energy_type(cls) -> type[FuelGasRate]:
        return FuelGasRate

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_rate(self) -> float:
        return self._rate

    def get_input_energy(self) -> FuelGasRate:
        return FuelGasRate(self._rate)


class Compressor(Consumer):
    """Compressor requiring mechanical power (driven by turbine or motor)."""

    def __init__(self, name: str, power: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._power = power
        self._id: Final[EnergyUnitId] = energy_unit_id or Compressor._create_id()

    @classmethod
    def get_input_energy_type(cls) -> type[MechanicalPower]:
        return MechanicalPower

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_power(self) -> float:
        return self._power

    def get_input_energy(self) -> MechanicalPower:
        return MechanicalPower(self._power)


class Pump(Consumer):
    """Pump requiring mechanical power (e.g. water injection pump)."""

    def __init__(self, name: str, power: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._power = power
        self._id: Final[EnergyUnitId] = energy_unit_id or Pump._create_id()

    @classmethod
    def get_input_energy_type(cls) -> type[MechanicalPower]:
        return MechanicalPower

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_power(self) -> float:
        return self._power

    def get_input_energy(self) -> MechanicalPower:
        return MechanicalPower(self._power)


class DieselConsumer(Consumer):
    """Direct diesel consumer (e.g. mobile rig, emergency generator)."""

    def __init__(self, name: str, rate: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._name = name
        self._rate = rate
        self._id: Final[EnergyUnitId] = energy_unit_id or DieselConsumer._create_id()

    @classmethod
    def get_input_energy_type(cls) -> type[DieselRate]:
        return DieselRate

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_rate(self) -> float:
        return self._rate

    def get_input_energy(self) -> DieselRate:
        return DieselRate(self._rate)
