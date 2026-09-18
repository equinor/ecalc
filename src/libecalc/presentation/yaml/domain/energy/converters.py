from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from libecalc.common.time_utils import Period
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_units import ElectricalMotor, GasTurbine, GeneratorSet
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(kw_only=True)
class TimeSeriesGeneratorSetFactory(TimeSeriesEnergyUnitFactory):
    power_to_fuel: Callable[[float], float] = lambda power: power

    def create(self, demand: Energy, capacity: Energy | None, **extra: Any) -> GeneratorSet:
        return GeneratorSet(
            name=self.name,
            power_to_fuel=self.power_to_fuel,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            capacity=capacity,
        )


@dataclass(kw_only=True)
class TimeSeriesGasTurbineFactory(TimeSeriesEnergyUnitFactory):
    power_to_fuel: Callable[[float], float] = lambda power: power

    def create(self, demand: Energy, capacity: Energy | None, **extra: Any) -> GasTurbine:
        return GasTurbine(
            name=self.name,
            power_to_fuel=self.power_to_fuel,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            capacity=capacity,
        )


@dataclass(kw_only=True)
class TimeSeriesElectricalMotorFactory(TimeSeriesEnergyUnitFactory):
    efficiency: TimeSeriesExpression | None = None

    def create(self, demand: Energy, capacity: Energy | None, **extra: Any) -> ElectricalMotor:
        period: Period = extra["period"]
        return ElectricalMotor(
            name=self.name,
            efficiency=self.efficiency.get_value(period) if self.efficiency is not None else None,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            capacity=capacity,
        )
