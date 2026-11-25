from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from libecalc.common.time_utils import Period
from libecalc.ecalc_model.model_event import EnergyUnitModelEvent, active_model, validate_unique_change_times
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import ElectricalPower, Energy, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import DieselEngine, ElectricalMotor, GasTurbine, Generator
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.energy.models.combustion_engine_fuel_model import DieselEngineFuelModel, TurbineFuelModel
from libecalc.energy.models.generator_set_fuel_model import GeneratorSetFuelModel
from libecalc.presentation.yaml.domain.energy.base import TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_optional_energy
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


def _own_model_events[ModelT](
    unit_description: str, energy_unit_id: EnergyUnitId, model_events: Sequence[EnergyUnitModelEvent[ModelT]]
) -> tuple[EnergyUnitModelEvent[ModelT], ...]:
    validate_unique_change_times(model_events)
    foreign_events = [event for event in model_events if event.change_target != energy_unit_id]
    if foreign_events:
        raise InvalidEnergyNetworkInputError(
            f"{unit_description} got model events targeting another energy unit: "
            f"{', '.join(str(event.change_target) for event in foreign_events)}."
        )
    return tuple(sorted(model_events, key=lambda event: event.change_time))


def _required_period(unit_description: str, extra: Mapping[str, Any]) -> Period:
    period = extra.get("period")
    if not isinstance(period, Period):
        raise InvalidEnergyNetworkInputError(f"{unit_description} needs a period, got {period!r}.")
    return period


class TimeSeriesGeneratorSetFactory(TimeSeriesEnergyUnitFactory):
    def __init__(
        self,
        *,
        name: str,
        fuel_model: GeneratorSetFuelModel,
        energy_unit_id: EnergyUnitId | None = None,
        input_energy_type: type[Energy],
        model_events: Sequence[EnergyUnitModelEvent[GeneratorSetFuelModel]] = (),
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.fuel_model = fuel_model
        self.input_energy_type = input_energy_type
        self.model_events = _own_model_events(f"Generator '{name}'", self.get_id(), model_events)

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> Generator:
        (incoming_connection,) = incoming_connections
        period = _required_period(f"Generator '{self.get_name()}'", extra)
        fuel_model = active_model(self.fuel_model, self.model_events, at=period.start)
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
        fuel_model: TurbineFuelModel,
        energy_unit_id: EnergyUnitId | None = None,
        model_events: Sequence[EnergyUnitModelEvent[TurbineFuelModel]] = (),
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.fuel_model = fuel_model
        self.model_events = _own_model_events(f"Gas turbine '{name}'", self.get_id(), model_events)

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> GasTurbine:
        (incoming_connection,) = incoming_connections
        period = _required_period(f"Gas turbine '{self.get_name()}'", extra)
        fuel_model = active_model(self.fuel_model, self.model_events, at=period.start)
        return GasTurbine(
            name=self.get_name(),
            power_to_fuel=fuel_model.fuel_for_power,
            energy_unit_id=self.get_id(),
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            capacity=MechanicalPower(fuel_model.max_power),
        )


class TimeSeriesDieselEngineFactory(TimeSeriesEnergyUnitFactory):
    def __init__(
        self,
        *,
        name: str,
        fuel_model: DieselEngineFuelModel,
        energy_unit_id: EnergyUnitId | None = None,
        model_events: Sequence[EnergyUnitModelEvent[DieselEngineFuelModel]] = (),
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.fuel_model = fuel_model
        self.model_events = _own_model_events(f"Diesel engine '{name}'", self.get_id(), model_events)

    def create(self, demand: Energy, *, incoming_connections: Sequence[EnergyConnection], **extra: Any) -> DieselEngine:
        (incoming_connection,) = incoming_connections
        period = _required_period(f"Diesel engine '{self.get_name()}'", extra)
        fuel_model = active_model(self.fuel_model, self.model_events, at=period.start)
        return DieselEngine(
            name=self.get_name(),
            power_to_fuel=fuel_model.fuel_for_power,
            energy_unit_id=self.get_id(),
            output_energy=demand,
            input_connection_id=incoming_connection.id,
            capacity=MechanicalPower(fuel_model.max_power),
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
