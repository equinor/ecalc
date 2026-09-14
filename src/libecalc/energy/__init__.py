"""New energy domain — will replace libecalc.domain.energy.

ABCs model a single operational point."""

from libecalc.energy.consumer import Consumer
from libecalc.energy.converter import Converter
from libecalc.energy.dispatch import Candidate, DispatchStrategy, PriorityDispatch
from libecalc.energy.energy_types import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId
from libecalc.energy.source import Source

__all__ = [
    "Candidate",
    "Consumer",
    "Converter",
    "DispatchStrategy",
    "Energy",
    "DieselRate",
    "ElectricalPower",
    "EnergyUnit",
    "EnergyUnitId",
    "FuelGasRate",
    "MechanicalPower",
    "PriorityDispatch",
    "Source",
]
