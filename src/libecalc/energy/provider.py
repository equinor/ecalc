from __future__ import annotations

import abc

from libecalc.energy.demand import Demand, ElectricalPower
from libecalc.energy.supply import Supply


class Provider[TDemand: Demand](abc.ABC):
    """Anything that supplies energy — from outside the system,
    by converting one energy type to another, or by distributing across providers."""

    @abc.abstractmethod
    def get_id(self) -> str: ...

    @abc.abstractmethod
    def supply(self, demand: TDemand) -> Supply[TDemand]: ...


class Source[TDemand: Demand](Provider[TDemand]):
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
    def input_demand(self, demand: TProvides) -> TRequires:
        """What is needed as input to deliver the demanded output."""
        ...


class Bus(Provider[ElectricalPower]):
    """Distributes electrical power across multiple providers with
    priority-based allocation.

    Only handles electrical power (switchboard/busbar concept).
    Fills demand from providers in order — the first provider is used
    up to its capacity before the next one is started.

    Example: cable from shore (priority 1) + generator set (priority 2).
    """

    ...
