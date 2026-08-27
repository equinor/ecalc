"""New energy domain — will replace libecalc.domain.energy.

ABCs model a single operational point. Time iteration is handled by the solver."""

from libecalc.energy.consumer import Consumer
from libecalc.energy.energy_types import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId
from libecalc.energy.provider import Converter, Provider, Source

__all__ = [
    "Consumer",
    "Converter",
    "Energy",
    "DieselRate",
    "ElectricalPower",
    "EnergyUnit",
    "EnergyUnitId",
    "FuelGasRate",
    "MechanicalPower",
    "Provider",
    "Source",
]
