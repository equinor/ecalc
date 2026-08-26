"""New energy domain — will replace libecalc.domain.energy.

ABCs model a single operational point. Time iteration is handled by the solver."""

from libecalc.energy.consumer import Consumer
from libecalc.energy.demand import Demand, DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId
from libecalc.energy.provider import Converter, Provider, Source

__all__ = [
    "Consumer",
    "Converter",
    "Demand",
    "DieselRate",
    "ElectricalPower",
    "EnergyUnit",
    "EnergyUnitId",
    "FuelGasRate",
    "MechanicalPower",
    "Provider",
    "Source",
]
