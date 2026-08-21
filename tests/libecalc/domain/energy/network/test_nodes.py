"""Unit tests for individual energy nodes (consumers and providers)."""

import pytest

from libecalc.domain.energy.network.energy_stream import EnergyStream, EnergyType
from libecalc.domain.energy.network.nodes.consumers import RotatingEquipment, Shaft
from libecalc.domain.energy.network.nodes.providers import ElectricMotor, Generator, Shore, Wind
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_model import GeneratorSetModel
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from tests.libecalc.domain.energy.network.conftest import SimpleFuelConverter

FUEL_PER_MW = 100.0  # Sm³/day per MW


class TestRotatingEquipment:
    def test_demand(self):
        eq = RotatingEquipment(demand=0.5)
        stream = eq.get_demand()
        assert stream.value == 0.5
        assert stream.energy_type == EnergyType.MECHANICAL

    def test_zero_demand(self):
        eq = RotatingEquipment(demand=0.0)
        assert eq.get_demand().value == 0.0


class TestShaft:
    def test_aggregates_demand(self):
        shaft = Shaft(
            rotating_equipment=[RotatingEquipment(demand=0.5), RotatingEquipment(demand=1.0)],
        )
        assert shaft.get_demand().value == 1.5

    def test_mechanical_efficiency(self):
        """0.5 MW through 50% efficient shaft → 1.0 MW demand."""
        shaft = Shaft(
            rotating_equipment=[RotatingEquipment(demand=0.5)],
            mechanical_efficiency=0.5,
        )
        assert shaft.get_demand().value == 1.0


class TestElectricMotor:
    def test_type_conversion(self):
        """Mechanical demand → electrical output."""
        demand = EnergyStream.mechanical(1.0)
        motor = ElectricMotor(efficiency=1.0, max_power_mw=10.0)
        supply = motor.supply(demand)
        assert supply.energy_type == EnergyType.ELECTRICAL
        assert supply.value == demand.value

    def test_efficiency_loss(self):
        """90% motor efficiency: 1.0 MW mechanical → 1.111 MW electrical."""
        demand = EnergyStream.mechanical(1.0)
        motor = ElectricMotor(efficiency=0.9, max_power_mw=10.0)
        supply = motor.supply(demand)
        assert supply.value == demand.value / 0.9

    def test_capacity_margin(self):
        motor = ElectricMotor(efficiency=0.9, max_power_mw=5.0)
        demand = EnergyStream.mechanical(1.0)
        assert motor.get_capacity_margin(demand) == 4.0


class TestGenerator:
    def test_fuel_from_power(self):
        """1.5 MW electrical → 150 Sm³/day fuel."""
        demand = EnergyStream.electrical(1.5)
        gen = Generator(generator=SimpleFuelConverter(fuel_per_mw=FUEL_PER_MW))
        supply = gen.supply(demand)
        assert supply.energy_type == EnergyType.FUEL
        assert supply.value == demand.value * FUEL_PER_MW

    def test_capacity_margin(self):
        """Generator capacity: 2.0 MW, demand: 1.5 MW → margin = 0.5 MW."""
        gen = Generator(generator=SimpleFuelConverter(fuel_per_mw=FUEL_PER_MW, max_power_mw=2.0))
        demand = EnergyStream.electrical(1.5)
        assert gen.get_capacity_margin(demand) == 2.0 - demand.value


class TestGeneratorWithGeneratorSetModel:
    """Tests using the real GeneratorSetModel (interpolation-based)."""

    @pytest.fixture
    def generator_model(self) -> GeneratorSetModel:
        """Linear: 100 Sm³/day per MW, max 5 MW."""
        return GeneratorSetModel(
            name="test_genset",
            resource=MemoryResource(headers=["POWER", "FUEL"], data=[[0, 5], [0, 500]]),
        )

    def test_fuel_from_power(self, generator_model):
        demand = EnergyStream.electrical(1.5)
        gen = Generator(generator=generator_model)
        supply = gen.supply(demand)
        assert supply.value == demand.value * 100.0  # 100 Sm³/day per MW

    def test_capacity_margin(self, generator_model):
        demand = EnergyStream.electrical(1.5)
        gen = Generator(generator=generator_model)
        assert gen.get_capacity_margin(demand) == 5 - demand.value  # Max power is 5 MW


class TestShore:
    def test_zero_fuel(self):
        demand = EnergyStream.electrical(3.0)
        supply = Shore(max_capacity_mw=10.0).supply(demand)
        assert supply.value == 0.0
        assert supply.energy_type == EnergyType.FUEL

    def test_capacity_margin(self):
        demand = EnergyStream.electrical(3.0)
        shore = Shore(max_capacity_mw=10.0)
        assert shore.get_capacity_margin(demand) == 10 - demand.value

    def test_cable_loss(self):
        """5% cable loss → 3 MW requires 3.15 MW from shore."""
        demand = EnergyStream.electrical(3.0)
        shore = Shore(max_capacity_mw=10.0, cable_loss_fraction=0.05)
        assert shore.get_capacity_margin(demand) == 10.0 - demand.value * 1.05

    def test_exceeds_capacity(self):
        shore = Shore(max_capacity_mw=2.0)
        assert shore.get_capacity_margin(EnergyStream.electrical(3.0)) < 0


class TestWind:
    def test_zero_fuel(self):
        demand = EnergyStream.electrical(2.0)
        supply = Wind(available_power_mw=5.0).supply(demand)
        assert supply.value == 0.0

    def test_capacity_margin(self):
        demand = EnergyStream.electrical(2.0)
        wind = Wind(available_power_mw=5.0)
        assert wind.get_capacity_margin(demand) == 5.0 - demand.value
