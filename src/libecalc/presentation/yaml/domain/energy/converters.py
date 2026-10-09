from __future__ import annotations

from collections.abc import Callable, Sequence

from libecalc.common.time_utils import Period
from libecalc.energy.energy_network_simulation import EnergyUnitFactory
from libecalc.energy.energy_network_topology import EnergyConnection
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import ElectricalMotor, GasTurbine, GeneratorSet
from libecalc.presentation.yaml.domain.energy.base import ResolvedEnergyUnitFactory, TimeSeriesEnergyUnitFactory
from libecalc.presentation.yaml.domain.energy.expressions import resolve_optional_efficiency, resolve_optional_energy
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TimeSeriesGeneratorSetFactory(TimeSeriesEnergyUnitFactory):
    def __init__(
        self,
        *,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
        power_to_fuel: Callable[[float], float] = lambda power: power,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id, capacity=capacity)
        self.power_to_fuel = power_to_fuel

    def resolve(self, period: Period) -> EnergyUnitFactory:
        capacity = resolve_optional_energy(
            self.capacity,
            GeneratorSet.get_output_energy_type(),
            period=period,
            description=f"Capacity for '{self.get_name()}'",
        )
        name, energy_unit_id, power_to_fuel = self.get_name(), self.get_id(), self.power_to_fuel

        def create(demand: Energy, incoming_connections: Sequence[EnergyConnection]) -> GeneratorSet:
            (incoming_connection,) = incoming_connections
            return GeneratorSet(
                name=name,
                power_to_fuel=power_to_fuel,
                energy_unit_id=energy_unit_id,
                output_energy=demand,
                input_connection_id=incoming_connection.id,
                capacity=capacity,
            )

        return ResolvedEnergyUnitFactory(energy_unit_id=energy_unit_id, name=name, create=create)


class TimeSeriesGasTurbineFactory(TimeSeriesEnergyUnitFactory):
    def __init__(
        self,
        *,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
        capacity: TimeSeriesExpression | None = None,
        power_to_fuel: Callable[[float], float] = lambda power: power,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id, capacity=capacity)
        self.power_to_fuel = power_to_fuel

    def resolve(self, period: Period) -> EnergyUnitFactory:
        capacity = resolve_optional_energy(
            self.capacity,
            GasTurbine.get_output_energy_type(),
            period=period,
            description=f"Capacity for '{self.get_name()}'",
        )
        name, energy_unit_id, power_to_fuel = self.get_name(), self.get_id(), self.power_to_fuel

        def create(demand: Energy, incoming_connections: Sequence[EnergyConnection]) -> GasTurbine:
            (incoming_connection,) = incoming_connections
            return GasTurbine(
                name=name,
                power_to_fuel=power_to_fuel,
                energy_unit_id=energy_unit_id,
                output_energy=demand,
                input_connection_id=incoming_connection.id,
                capacity=capacity,
            )

        return ResolvedEnergyUnitFactory(energy_unit_id=energy_unit_id, name=name, create=create)


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

    def resolve(self, period: Period) -> EnergyUnitFactory:
        efficiency = resolve_optional_efficiency(
            self.efficiency, period=period, description=f"Efficiency for '{self.get_name()}'"
        )
        capacity = resolve_optional_energy(
            self.capacity,
            ElectricalMotor.get_output_energy_type(),
            period=period,
            description=f"Capacity for '{self.get_name()}'",
        )

        name, energy_unit_id = self.get_name(), self.get_id()

        def create(demand: Energy, incoming_connections: Sequence[EnergyConnection]) -> ElectricalMotor:
            (incoming_connection,) = incoming_connections
            return ElectricalMotor(
                name=name,
                efficiency=efficiency,
                energy_unit_id=energy_unit_id,
                output_energy=demand,
                input_connection_id=incoming_connection.id,
                capacity=capacity,
            )

        return ResolvedEnergyUnitFactory(energy_unit_id=energy_unit_id, name=name, create=create)
