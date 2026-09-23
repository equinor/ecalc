from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from libecalc.common.time_utils import Period
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_units import ElectricalMotor, GasTurbine, GeneratorSet
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_optional_energy
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(kw_only=True)
class TimeSeriesGeneratorSetFactory(TimeSeriesEnergyUnitFactory):
    capacity: TimeSeriesExpression | None = None
    power_to_fuel: Callable[[float], float] = lambda power: power

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> GeneratorSet:
        (incoming_connection,) = incoming_connections
        return GeneratorSet(
            name=self.name,
            power_to_fuel=self.power_to_fuel,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            capacity=resolve_optional_energy(
                self.capacity,
                GeneratorSet.get_output_energy_type(),
                period=extra.get("period"),
                description=f"Capacity for '{self.name}'",
            ),
        )


@dataclass(kw_only=True)
class TimeSeriesGasTurbineFactory(TimeSeriesEnergyUnitFactory):
    capacity: TimeSeriesExpression | None = None
    power_to_fuel: Callable[[float], float] = lambda power: power

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> GasTurbine:
        (incoming_connection,) = incoming_connections
        return GasTurbine(
            name=self.name,
            power_to_fuel=self.power_to_fuel,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            capacity=resolve_optional_energy(
                self.capacity,
                GasTurbine.get_output_energy_type(),
                period=extra.get("period"),
                description=f"Capacity for '{self.name}'",
            ),
        )


@dataclass(kw_only=True)
class TimeSeriesElectricalMotorFactory(TimeSeriesEnergyUnitFactory):
    capacity: TimeSeriesExpression | None = None
    efficiency: TimeSeriesExpression | None = None

    def create(
        self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any
    ) -> ElectricalMotor:
        (incoming_connection,) = incoming_connections
        period: Period = extra["period"]
        return ElectricalMotor(
            name=self.name,
            efficiency=self.efficiency.get_value(period) if self.efficiency is not None else None,
            energy_unit_id=self.energy_unit_id,
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            capacity=resolve_optional_energy(
                self.capacity,
                ElectricalMotor.get_output_energy_type(),
                period=extra.get("period"),
                description=f"Capacity for '{self.name}'",
            ),
        )
