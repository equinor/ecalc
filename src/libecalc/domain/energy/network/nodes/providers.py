import numpy as np

from libecalc.domain.energy.infrastructure_contracts import FuelConverter, TurbineDriver
from libecalc.domain.energy.network.energy_node import EnergyNodeId, Provider, create_energy_node_id
from libecalc.domain.energy.network.energy_stream import EnergyStream, EnergyType


class ElectricMotor(Provider):
    """Converts mechanical demand to electrical demand, adjusted for motor efficiency losses."""

    def __init__(self, efficiency: float, max_power_mw: float):
        self._id = create_energy_node_id()
        self._efficiency = efficiency
        self._max_power_mw = max_power_mw

    def get_id(self) -> EnergyNodeId:
        return self._id

    def supply(self, demand: EnergyStream) -> EnergyStream:
        if demand.energy_type != EnergyType.MECHANICAL:
            raise ValueError(f"Electric motor expects mechanical demand, got {demand.energy_type}")
        return EnergyStream.electrical(demand.value / self._efficiency)

    def get_capacity_margin(self, demand: EnergyStream) -> float:
        """Spare motor capacity in MW. Negative means demand exceeds motor rating."""
        return self._max_power_mw - demand.value


class Generator(Provider):
    """Converts electrical demand to fuel consumption via a generator set."""

    def __init__(self, generator: FuelConverter):
        self._id = create_energy_node_id()
        self._generator = generator

    def get_id(self) -> EnergyNodeId:
        return self._id

    def supply(self, demand: EnergyStream) -> EnergyStream:
        if demand.energy_type != EnergyType.ELECTRICAL:
            raise ValueError(f"Generator expects electrical demand, got {demand.energy_type}")
        return EnergyStream.fuel(self._generator.evaluate_fuel_usage(demand.value))

    def get_capacity_margin(self, demand: EnergyStream) -> float:
        """Spare capacity in MW. Negative means demand exceeds what this generator can deliver."""
        return self._generator.evaluate_power_capacity_margin(demand.value)


class Turbine(Provider):
    """Converts mechanical demand to fuel consumption via a gas turbine."""

    def __init__(self, turbine: TurbineDriver):
        self._id = create_energy_node_id()
        self._turbine = turbine

    def get_id(self) -> EnergyNodeId:
        return self._id

    def supply(self, demand: EnergyStream) -> EnergyStream:
        if demand.energy_type != EnergyType.MECHANICAL:
            raise ValueError(f"Turbine expects mechanical demand, got {demand.energy_type}")
        result = self._turbine.evaluate(load=np.array([demand.value]))
        energy_result = result.get_energy_result()
        return EnergyStream.fuel(energy_result.energy_usage.values[0])

    def get_capacity_margin(self, demand: EnergyStream) -> float:
        """Spare turbine capacity in MW. Negative means demand exceeds turbine rating."""
        return self._turbine.max_power - demand.value


class Shore(Provider):
    """Power from shore: zero fuel, limited by cable capacity."""

    def __init__(self, max_capacity_mw: float, cable_loss_fraction: float = 0.0):
        self._id = create_energy_node_id()
        self._max_capacity_mw = max_capacity_mw
        self._cable_loss_fraction = cable_loss_fraction

    def get_id(self) -> EnergyNodeId:
        return self._id

    def supply(self, demand: EnergyStream) -> EnergyStream:
        if demand.energy_type != EnergyType.ELECTRICAL:
            raise ValueError(f"Power from shore expects electrical demand, got {demand.energy_type}")
        # Shore power produces zero fuel — the energy comes from the land grid.
        return EnergyStream.fuel(0.0)

    def get_capacity_margin(self, demand: EnergyStream) -> float:
        """Spare cable capacity in MW. Negative means demand exceeds cable rating."""
        power_from_shore = demand.value * (1 + self._cable_loss_fraction)
        return self._max_capacity_mw - power_from_shore


class Wind(Provider):
    """Offshore wind: zero fuel, capacity set at construction."""

    def __init__(self, available_power_mw: float):
        self._id = create_energy_node_id()
        self._available_power_mw = available_power_mw

    def get_id(self) -> EnergyNodeId:
        return self._id

    def supply(self, demand: EnergyStream) -> EnergyStream:
        if demand.energy_type != EnergyType.ELECTRICAL:
            raise ValueError(f"Wind power expects electrical demand, got {demand.energy_type}")
        # Wind produces zero fuel — energy comes from the turbines.
        return EnergyStream.fuel(0.0)

    def get_capacity_margin(self, demand: EnergyStream) -> float:
        """Spare wind capacity in MW. Negative means demand exceeds available wind power."""
        return self._available_power_mw - demand.value
