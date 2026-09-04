from __future__ import annotations

import abc

from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit


class Converter(EnergyUnit, abc.ABC):
    """Converts one energy type to another.

    input_energy_type is what this converter needs as input,
    output_energy_type is what it delivers.

    Examples:
        GeneratorSet: input FuelGasRate, output ElectricalPower
        GasTurbine: input FuelGasRate, output MechanicalPower
        ElectricalMotor: input ElectricalPower, output MechanicalPower
    """

    @classmethod
    @abc.abstractmethod
    def get_input_energy_type(cls) -> type[Energy]: ...

    @classmethod
    @abc.abstractmethod
    def get_output_energy_type(cls) -> type[Energy]: ...

    @abc.abstractmethod
    def get_input_energy(self, output_energy: Energy) -> Energy:
        """Given output needed, what input is required?"""
        ...

    @abc.abstractmethod
    def capacity(self) -> Energy | None:
        """Maximum this converter can deliver. None = unlimited."""
        ...
