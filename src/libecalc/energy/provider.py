from __future__ import annotations

import abc

from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit


class Provider(EnergyUnit, abc.ABC):
    """Anything that supplies energy — from outside the system,
    by converting one energy type to another, or by distributing across providers."""

    @classmethod
    @abc.abstractmethod
    def get_output_energy_type(cls) -> type[Energy]: ...

    @abc.abstractmethod
    def capacity(self) -> Energy | None:
        """Maximum this provider can deliver. None = unlimited."""
        ...

    @property
    @abc.abstractmethod
    def provided_demand_type(self) -> type[TProvides]: ...


class Source(Provider):
    """Energy enters the system from an external source.

    Examples: power from shore (ElectricalPower), fuel gas supply (FuelGasRate).
    """

    ...


class Converter(Provider):
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

    @abc.abstractmethod
    def get_input_energy(self, output_energy: Energy) -> Energy:
        """Given output needed, what input is required?"""
        ...

    @property
    @abc.abstractmethod
    def required_demand_type(self) -> type[TRequires]: ...
