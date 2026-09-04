"""New energy domain — will replace libecalc.domain.energy.

ABCs model a single operational point."""

from libecalc.energy.dispatch import DispatchStrategy, PriorityDispatch, ProviderAvailability
from libecalc.energy.energy_types import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId
from libecalc.energy.roles import Consumer, Converter, DerivedInputProvider, Junction, Provider, Source, Transporter

__all__ = [
    "Consumer",
    "Converter",
    "DerivedInputProvider",
    "DispatchStrategy",
    "Energy",
    "DieselRate",
    "ElectricalPower",
    "EnergyUnit",
    "EnergyUnitId",
    "FuelGasRate",
    "Junction",
    "MechanicalPower",
    "PriorityDispatch",
    "Provider",
    "ProviderAvailability",
    "Source",
    "Transporter",
]
