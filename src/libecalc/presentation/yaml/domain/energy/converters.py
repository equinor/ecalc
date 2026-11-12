from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from libecalc.common.time_utils import Period
from libecalc.ecalc_model.model_event import EnergyUnitModelEvent, active_model, validate_unique_change_times
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import ElectricalPower, Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import ElectricalMotor, GasTurbine, Generator
from libecalc.energy.errors import InvalidEnergyNetworkInputError
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
        input_energy_type: type[Energy],
        model_events: Sequence[EnergyUnitModelEvent[GeneratorFuelModel]] = (),
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.fuel_model = fuel_model
        self.input_energy_type = input_energy_type
        validate_unique_change_times(model_events)
        foreign_events = [event for event in model_events if event.change_target != self.get_id()]
        if foreign_events:
            raise InvalidEnergyNetworkInputError(
                f"Generator '{name}' got model events targeting another energy unit: "
                f"{', '.join(str(event.change_target) for event in foreign_events)}."
            )
        self.model_events = tuple(sorted(model_events, key=lambda event: event.change_time))

    def _fuel_model_for(self, period: Period | None) -> GeneratorFuelModel:
        if not self.model_events:
            return self.fuel_model
        if period is None:
            raise InvalidEnergyNetworkInputError(
                f"Generator '{self.get_name()}' changes model over time but no period was given to select a model."
            )
        return active_model(self.fuel_model, self.model_events, at=period.start)

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> Generator:
        (incoming_connection,) = incoming_connections
        period = extra.get("period")
        fuel_model = self._fuel_model_for(period)
        return Generator(
            name=self.get_name(),
            power_to_fuel=fuel_model.fuel_for_power,
            input_energy_type=self.input_energy_type,
            energy_unit_id=self.get_id(),
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            capacity=ElectricalPower(fuel_model.max_power),
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
