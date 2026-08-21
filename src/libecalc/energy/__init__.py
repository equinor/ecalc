"""New energy domain — will replace libecalc.domain.energy.

ABCs model a single operational point. Time iteration is handled by the solver."""

from libecalc.energy.consumer import Consumer
from libecalc.energy.demand import Demand, DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.provider import Bus, Converter, Provider, Source
from libecalc.energy.supply import Supply

__all__ = [
    "Bus",
    "Consumer",
    "Converter",
    "Demand",
    "DieselRate",
    "ElectricalPower",
    "FuelGasRate",
    "MechanicalPower",
    "Provider",
    "Source",
    "Supply",
]
