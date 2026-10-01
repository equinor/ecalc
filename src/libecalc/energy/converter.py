from __future__ import annotations

import abc
from collections.abc import Callable
from typing import Final

from libecalc.energy.energy_failure import EnergyFailure, capacity_failures
from libecalc.energy.energy_types import ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnit
from libecalc.energy.ids import EnergyConnectionId, EnergyUnitId

# Energy type pairs for which real equipment exists, e.g. no equipment converts electricity into fuel gas or diesel.
KNOWN_CONVERSIONS: Final[frozenset[tuple[type[Energy], type[Energy]]]] = frozenset(
    {
        (FuelGasRate, ElectricalPower),  # generator set
        (FuelGasRate, MechanicalPower),  # gas turbine
        (ElectricalPower, MechanicalPower),  # electrical motor
    }
)


class Conversion(abc.ABC):
    @abc.abstractmethod
    def input_for(self, output: float) -> float: ...


class SampledConversion(Conversion):
    """Input from a sampled curve, e.g. a generator set or gas turbine's power-to-fuel curve."""

    def __init__(self, curve: Callable[[float], float]) -> None:
        self._curve = curve

    def input_for(self, output: float) -> float:
        return self._curve(output)


class EfficiencyConversion(Conversion):
    """Input from a constant efficiency ratio, e.g. an electrical motor."""

    def __init__(self, efficiency: float) -> None:
        self._efficiency = efficiency

    def input_for(self, output: float) -> float:
        return output / self._efficiency


class Converter(EnergyUnit):
    """Converts one energy type to another; the conversion decides how the input is derived from the output."""

    def __init__(
        self,
        name: str,
        output_energy: Energy,
        *,
        input_connection_id: EnergyConnectionId,
        input_energy_type: type[Energy],
        output_energy_type: type[Energy],
        conversion: Conversion,
        capacity: Energy | None = None,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name, energy_unit_id)
        if not isinstance(output_energy, output_energy_type):
            raise ValueError(
                f"Converter '{name}' declared output_energy_type={output_energy_type.__name__} but received "
                f"output_energy of type {type(output_energy).__name__}"
            )
        if (input_energy_type, output_energy_type) not in KNOWN_CONVERSIONS:
            raise ValueError(
                f"Converter '{name}' has no known equipment converting "
                f"{input_energy_type.__name__} to {output_energy_type.__name__}"
            )
        self._output_energy = output_energy
        self._input_connection_id = input_connection_id
        self._input_energy_type = input_energy_type
        self._output_energy_type = output_energy_type
        self._conversion = conversion
        self._capacity = capacity

    def get_output_energy(self) -> Energy:
        return self._output_energy

    def get_capacity(self) -> Energy | None:
        return self._capacity

    def get_failures(self) -> list[EnergyFailure]:
        return capacity_failures(self._output_energy, self._capacity)

    def get_input_energy_type(self) -> type[Energy]:
        return self._input_energy_type

    def get_output_energy_type(self) -> type[Energy]:
        return self._output_energy_type

    def get_input_energies(self) -> dict[EnergyConnectionId, Energy]:
        return {
            self._input_connection_id: self._input_energy_type(self._conversion.input_for(self._output_energy.value))
        }
