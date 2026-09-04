from collections.abc import Callable

from libecalc.energy.converter import Converter
from libecalc.energy.energy_types import ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId


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
        super().__init__(name, energy_unit_id)
        self._max_power = max_power
        self._power_to_fuel = power_to_fuel

    @classmethod
    def get_input_energy_type(cls) -> type[FuelGasRate]:
        return FuelGasRate

    @classmethod
    def get_output_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

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
        super().__init__(name, energy_unit_id)
        self._max_power = max_power
        self._power_to_fuel = power_to_fuel

    @classmethod
    def get_input_energy_type(cls) -> type[FuelGasRate]:
        return FuelGasRate

    @classmethod
    def get_output_energy_type(cls) -> type[MechanicalPower]:
        return MechanicalPower

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
        super().__init__(name, energy_unit_id)
        self._max_power = max_power
        self._efficiency = efficiency

    @classmethod
    def get_input_energy_type(cls) -> type[ElectricalPower]:
        return ElectricalPower

    @classmethod
    def get_output_energy_type(cls) -> type[MechanicalPower]:
        return MechanicalPower

    def get_max_power(self) -> float:
        return self._max_power

    def get_efficiency(self) -> float:
        return self._efficiency

    def capacity(self) -> MechanicalPower | None:
        return MechanicalPower(self._max_power)

    def get_input_energy(self, output_energy: MechanicalPower) -> ElectricalPower:
        return ElectricalPower(output_energy.value / self._efficiency)
