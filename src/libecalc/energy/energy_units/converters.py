from collections.abc import Callable
from typing import Final

from libecalc.energy.demand import Demand, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.provider import Converter


class Transporter[T: Demand](Converter[T, T]):
    """Moves energy without changing form, possibly with loss.

    Examples:
        Transporter[ElectricalPower] — subsea cable
        Transporter[FuelGasRate] — fuel gas pipeline
        Transporter[MechanicalPower] — shaft with bearing/gearbox losses
    """

    ...


class ElectricalCable(Transporter[ElectricalPower]):
    """Electrical cable with transmission loss (e.g. subsea cable from shore)."""

    def __init__(
        self, name: str, max_power: float, loss_fraction: float = 0.0, energy_unit_id: EnergyUnitId | None = None
    ) -> None:
        self._name = name
        self._max_power = max_power
        self._loss_fraction = loss_fraction
        self._id: Final[EnergyUnitId] = energy_unit_id or ElectricalCable._create_id()

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

    def get_input_demand(self, output_demand: ElectricalPower) -> ElectricalPower:
        return ElectricalPower(output_demand.value / (1 - self._loss_fraction))


class GeneratorSet(Converter[FuelGasRate, ElectricalPower]):
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

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_max_power(self) -> float:
        return self._max_power

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self._max_power)

    def get_input_demand(self, output_demand: ElectricalPower) -> FuelGasRate:
        return FuelGasRate(self._power_to_fuel(output_demand.value))


class GasTurbine(Converter[FuelGasRate, MechanicalPower]):
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

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_max_power(self) -> float:
        return self._max_power

    def capacity(self) -> MechanicalPower | None:
        return MechanicalPower(self._max_power)

    def get_input_demand(self, output_demand: MechanicalPower) -> FuelGasRate:
        return FuelGasRate(self._power_to_fuel(output_demand.value))


class ElectricalMotor(Converter[ElectricalPower, MechanicalPower]):
    """Electrical motor converting electrical power to mechanical power."""

    def __init__(
        self, name: str, max_power: float, efficiency: float = 0.95, energy_unit_id: EnergyUnitId | None = None
    ) -> None:
        self._name = name
        self._max_power = max_power
        self._efficiency = efficiency
        self._id: Final[EnergyUnitId] = energy_unit_id or ElectricalMotor._create_id()

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

    def get_input_demand(self, output_demand: MechanicalPower) -> ElectricalPower:
        return ElectricalPower(output_demand.value / self._efficiency)
