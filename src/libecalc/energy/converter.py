from __future__ import annotations

import abc

from libecalc.energy.energy_failure import EnergyFailure, capacity_failures
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit
from libecalc.energy.ids import EnergyConnectionId, EnergyUnitId


class Converter(EnergyUnit, abc.ABC):
    """Converts one energy type to another.

    input_energy_type is what this converter needs as input,
    output_energy_type is what it delivers.

    Examples:
        GeneratorSet: input FuelGasRate, output ElectricalPower
        GasTurbine: input FuelGasRate, output MechanicalPower
        ElectricalMotor: input ElectricalPower, output MechanicalPower
    """

    def __init__(
        self,
        name: str,
        output_energy: Energy,
        *,
        input_connection_id: EnergyConnectionId,
        capacity: Energy | None = None,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name, energy_unit_id)
        self._output_energy = output_energy
        self._input_connection_id = input_connection_id
        self._capacity = capacity

    def get_output_energy(self) -> Energy:
        return self._output_energy

    def get_capacity(self) -> Energy | None:
        return self._capacity

    def get_failures(self) -> list[EnergyFailure]:
        return capacity_failures(self._output_energy, self._capacity)

    @classmethod
    @abc.abstractmethod
    def get_input_energy_type(cls) -> type[Energy]: ...

    @classmethod
    @abc.abstractmethod
    def get_output_energy_type(cls) -> type[Energy]: ...
