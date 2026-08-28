import abc
from collections.abc import Callable
from typing import Final

from libecalc.energy.energy_types import ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.provider import Converter


class Transporter(Converter):
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


class ElectricalCable(Transporter):
    """Electrical cable with transmission loss (e.g. subsea cable from shore)."""

    def __init__(
        self, name: str, max_power: float, loss_fraction: float = 0.0, energy_unit_id: EnergyUnitId | None = None
    ) -> None:
        self._name = name
        self._max_power = max_power
        self._loss_fraction = loss_fraction
        self._id: Final[EnergyUnitId] = energy_unit_id or ElectricalCable._create_id()

    @classmethod
    def get_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_max_power(self) -> float:
        return self._max_power

    def get_loss_fraction(self) -> float:
        return self._loss_fraction

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self._max_power)

    def get_input_energy(self, output_energy: ElectricalPower) -> ElectricalPower:
        return ElectricalPower(output_energy.value / (1 - self._loss_fraction))


class GeneratorSet(Converter):
    """Gas-fired generator set converting fuel gas to electrical power.

    The power_to_fuel curve determines the fuel consumption characteristic.
    A smooth curve represents a single generator unit; a stepped curve with
    discontinuities can encode multiple physical generators switching on at
    load breakpoints (as in the legacy eCalc model).

    Alternatively, individual generators can be modelled as separate
    GeneratorSet instances connected to the same bus. The network solver's
    priority dispatch will then fill them one by one in connection order,
    invoking additional units only when prior ones reach capacity.
    """

    def __init__(
        self,
        name: str,
        max_power: float,
        power_to_fuel: Callable[[float], float],
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        self._name = name
        self._max_power = max_power
        self._power_to_fuel = power_to_fuel
        self._id: Final[EnergyUnitId] = energy_unit_id or GeneratorSet._create_id()

    @classmethod
    def get_input_energy_type(cls) -> type[FuelGasRate]:
        return FuelGasRate

    @classmethod
    def get_output_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_max_power(self) -> float:
        return self._max_power

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self._max_power)

    def get_input_energy(self, output_energy: ElectricalPower) -> FuelGasRate:
        return FuelGasRate(self._power_to_fuel(output_energy.value))


class GasTurbine(Converter):
    """Gas turbine converting fuel gas to mechanical power (e.g. for compressor drive)."""

    def __init__(
        self,
        name: str,
        max_power: float,
        power_to_fuel: Callable[[float], float],
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        self._name = name
        self._max_power = max_power
        self._power_to_fuel = power_to_fuel
        self._id: Final[EnergyUnitId] = energy_unit_id or GasTurbine._create_id()

    @classmethod
    def get_input_energy_type(cls) -> type[FuelGasRate]:
        return FuelGasRate

    @classmethod
    def get_output_energy_type(cls) -> type[MechanicalPower]:
        return MechanicalPower

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_max_power(self) -> float:
        return self._max_power

    def capacity(self) -> MechanicalPower | None:
        return MechanicalPower(self._max_power)

    def get_input_energy(self, output_energy: MechanicalPower) -> FuelGasRate:
        return FuelGasRate(self._power_to_fuel(output_energy.value))


class ElectricalMotor(Converter):
    """Electrical motor converting electrical power to mechanical power."""

    def __init__(
        self, name: str, max_power: float, efficiency: float = 0.95, energy_unit_id: EnergyUnitId | None = None
    ) -> None:
        self._name = name
        self._max_power = max_power
        self._efficiency = efficiency
        self._id: Final[EnergyUnitId] = energy_unit_id or ElectricalMotor._create_id()

    @classmethod
    def get_input_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

    @classmethod
    def get_output_energy_type(cls) -> type[MechanicalPower]:
        return MechanicalPower

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_max_power(self) -> float:
        return self._max_power

    def get_efficiency(self) -> float:
        return self._efficiency

    def capacity(self) -> MechanicalPower | None:
        return MechanicalPower(self._max_power)

    def get_input_energy(self, output_energy: MechanicalPower) -> ElectricalPower:
        return ElectricalPower(output_energy.value / self._efficiency)
