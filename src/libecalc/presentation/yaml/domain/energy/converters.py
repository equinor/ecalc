from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from libecalc.common.time_utils import Period
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import ElectricalMotor, GasTurbine, Generator
from libecalc.energy.models.fuel_power_curve import FuelPowerCurve
from libecalc.energy.models.generator_fuel_model import GeneratorFuelModel
from libecalc.energy.models.turbine_fuel_model import TurbineFuelModel
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_optional_energy
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TimeSeriesGeneratorFactory(TimeSeriesEnergyUnitFactory):
    def __init__(
        self,
        *,
        name: str,
        fuel_model: GeneratorFuelModel,
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id, capacity=capacity)
        self.fuel_model = fuel_model

    @property
    def power_to_fuel(self) -> Callable[[float], float]:
        return self.fuel_model.fuel_for_power

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> Generator:
        (incoming_connection,) = incoming_connections
        capacity = resolve_optional_energy(
            self.capacity,
            Generator.get_output_energy_type(),
            period=extra.get("period"),
            description=f"Capacity for '{self.get_name()}'",
        )
        return Generator(
            name=self.get_name(),
            power_to_fuel=self.power_to_fuel,
            energy_unit_id=self.get_id(),
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            capacity=capacity,
        )


class TimeSeriesGasTurbineFactory(TimeSeriesEnergyUnitFactory):
    def __init__(
        self,
        *,
        name: str,
        fuel_model: TurbineFuelModel | FuelPowerCurve,
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id, capacity=capacity)
        self.fuel_model = fuel_model

    @property
    def power_to_fuel(self) -> Callable[[float], float]:
        return self.fuel_model.fuel_for_power

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> GasTurbine:
        (incoming_connection,) = incoming_connections
        capacity = resolve_optional_energy(
            self.capacity,
            GasTurbine.get_output_energy_type(),
            period=extra.get("period"),
            description=f"Capacity for '{self.get_name()}'",
        )
        return GasTurbine(
            name=self.get_name(),
            power_to_fuel=self.power_to_fuel,
            energy_unit_id=self.get_id(),
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            capacity=capacity,
        )


class TimeSeriesElectricalMotorFactory(TimeSeriesEnergyUnitFactory):
    def __init__(
        self,
        *,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
        efficiency: TimeSeriesExpression | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id, capacity=capacity)
        self.efficiency = efficiency

    def create(
        self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any
    ) -> ElectricalMotor:
        (incoming_connection,) = incoming_connections
        period: Period = extra["period"]
        return ElectricalMotor(
            name=self.get_name(),
            efficiency=self.efficiency.get_value(period) if self.efficiency is not None else None,
            energy_unit_id=self.get_id(),
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            capacity=resolve_optional_energy(
                self.capacity,
                ElectricalMotor.get_output_energy_type(),
                period=extra.get("period"),
                description=f"Capacity for '{self.get_name()}'",
            ),
        )
