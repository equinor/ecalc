from __future__ import annotations

import abc
from uuid import UUID

from libecalc.energy.demand import Demand


class Provider[TProvides: Demand](abc.ABC):
    """Anything that supplies energy — from outside the system,
    by converting one energy type to another, or by distributing across providers."""

    @abc.abstractmethod
    def get_id(self) -> UUID: ...

    @abc.abstractmethod
    def capacity(self) -> TProvides | None:
        """Maximum this provider can deliver. None = unlimited."""
        ...


class Source[TProvides: Demand](Provider[TProvides]):
    """Energy enters the system from an external source.

    Examples: power from shore (ElectricalPower), fuel gas supply (FuelGasRate).
    """

    ...


class Converter[TRequires: Demand, TProvides: Demand](Provider[TProvides]):
    """Converts one energy type to another.

    TRequires is what this converter needs as input, TProvides is what it delivers.

    Examples:
        Converter[ElectricalPower, MechanicalPower] — electric motor
        Converter[FuelGasRate, ElectricalPower] — generator set
        Converter[FuelGasRate, MechanicalPower] — gas turbine
    """

    @abc.abstractmethod
    def get_input_demand(self, output_demand: TProvides) -> TRequires:
        """Given output needed, what input is required?"""
        ...
