"""End-to-end tests: Consumer → SerialEnergySystem → fuel."""

import pytest

from libecalc.domain.energy.network.energy_stream import EnergyStream, EnergyType
from libecalc.domain.energy.network.energy_system import EnergyChain, PowerBus, SerialEnergySystem
from libecalc.domain.energy.network.nodes.consumers import RotatingEquipment, Shaft
from libecalc.domain.energy.network.nodes.providers import ElectricMotor, Generator, Shore
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_model import GeneratorSetModel
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from tests.libecalc.domain.energy.network.conftest import SimpleFuelConverter

FUEL_PER_MW = 100.0  # Sm³/day per MW


@pytest.fixture
def generator_model() -> GeneratorSetModel:
    """Linear: 100 Sm³/day per MW, max 5 MW."""
    return GeneratorSetModel(
        name="genset",
        resource=MemoryResource(headers=["POWER", "FUEL"], data=[[0, 5], [0, 500]]),
    )


class TestSerialEnergySystem:
    def test_motor_to_generator(self):
        """1.5 MW mechanical → motor (100%) → 1.5 MW electrical → generator → fuel.

        fuel = 1.5 MW × 100 Sm³/day/MW = 150 Sm³/day
        """
        system = SerialEnergySystem(
            nodes=[
                ElectricMotor(efficiency=1.0, max_power_mw=10.0),
                Generator(generator=SimpleFuelConverter(fuel_per_mw=FUEL_PER_MW)),
            ]
        )
        supply = system.supply(EnergyStream.mechanical(1.5))

        assert supply.energy_type == EnergyType.FUEL
        assert supply.value == 1.5 * FUEL_PER_MW

    def test_motor_efficiency_propagates(self):
        """90% motor: 1.0 MW mechanical → 1.111 MW electrical → fuel.

        electrical = 1.0 / 0.90 = 1.111 MW
        fuel = 1.111 × 100 = 111.1 Sm³/day
        """
        demand = EnergyStream.mechanical(1.0)
        system = SerialEnergySystem(
            nodes=[
                ElectricMotor(efficiency=0.9, max_power_mw=10.0),
                Generator(generator=SimpleFuelConverter(fuel_per_mw=FUEL_PER_MW)),
            ]
        )
        supply = system.supply(demand)

        assert supply.value == demand.value / 0.9 * FUEL_PER_MW

    def test_multiple_rotating_equipment(self):
        """Shaft aggregates demand from multiple equipment.

        shaft: 1.5 + 0.5 = 2.0 MW mechanical
        motor: 2.0 / 0.90 = 2.222 MW electrical
        fuel: 2.222 × 100 = 222.2 Sm³/day
        """
        shaft = Shaft(
            rotating_equipment=[
                RotatingEquipment(demand=1.5),
                RotatingEquipment(demand=0.5),
            ]
        )
        system = SerialEnergySystem(
            nodes=[
                ElectricMotor(efficiency=0.90, max_power_mw=10.0),
                Generator(generator=SimpleFuelConverter(fuel_per_mw=FUEL_PER_MW)),
            ]
        )

        assert shaft.get_demand().value == 2.0
        supply = system.supply(shaft.get_demand())

        assert supply.value == (2.0 / 0.90) * FUEL_PER_MW

    def test_capacity_margin(self):
        """Tightest margin across the chain.

        demand: 1.0 MW mechanical
        motor margin: 10.0 - 1.0 = 9.0 MW
        electrical demand: 1.0 / 0.90 = 1.111 MW
        generator margin: 2.0 - 1.111 = 0.889 MW (tightest)
        system margin = min(9.0, 0.889) = 0.889 MW
        """
        system = SerialEnergySystem(
            nodes=[
                ElectricMotor(efficiency=0.90, max_power_mw=10.0),
                Generator(generator=SimpleFuelConverter(fuel_per_mw=FUEL_PER_MW, max_power_mw=2.0)),
            ]
        )
        demand = EnergyStream.mechanical(1.0)

        assert system.get_capacity_margin(demand) == 2.0 - demand.value / 0.90

    def test_shore_and_generator_split(self):
        """Shore covers 1 MW (zero fuel), generator covers rest.

        shaft: 2.0 MW mechanical
        motor: 2.0 / 0.90 = 2.222 MW electrical
        shore: 1.0 MW → 0 Sm³/day
        generator: 2.222 - 1.0 = 1.222 MW → 1.222 × 100 = 122.2 Sm³/day
        """
        shaft = Shaft(rotating_equipment=[RotatingEquipment(demand=2.0)])
        system = SerialEnergySystem(
            nodes=[
                ElectricMotor(efficiency=0.90, max_power_mw=10.0),
                PowerBus(
                    sources=[
                        Shore(max_capacity_mw=1.0),
                        Generator(generator=SimpleFuelConverter(fuel_per_mw=FUEL_PER_MW)),
                    ]
                ),
            ]
        )
        supply = system.supply(shaft.get_demand())

        electrical_demand = 2.0 / 0.90
        generator_load = electrical_demand - 1.0
        assert supply.value == generator_load * FUEL_PER_MW

    def test_with_real_generator_set_model(self, generator_model):
        """End-to-end with interpolation-based GeneratorSetModel.

        shaft: 1.5 MW mechanical
        motor (95%): 1.5 / 0.95 = 1.579 MW electrical
        generator: 1.579 × 100 = 157.9 Sm³/day (from [0,5] MW → [0,500] Sm³/day table)
        """
        shaft = Shaft(rotating_equipment=[RotatingEquipment(demand=1.5)])
        system = SerialEnergySystem(
            nodes=[
                ElectricMotor(efficiency=0.95, max_power_mw=10.0),
                Generator(generator=generator_model),
            ]
        )
        supply = system.supply(shaft.get_demand())

        assert supply.value == (1.5 / 0.95) * FUEL_PER_MW


class TestEnergyChain:
    def test_run(self):
        """Full chain: shaft → motor → generator → fuel + capacity margin.

        shaft: 1.0 / 0.95 = 1.053 MW mechanical
        motor: 1.053 / 0.90 = 1.170 MW electrical
        fuel: 1.170 × 100 = 116.96 Sm³/day
        """
        demand = 1.0
        shaft = Shaft(rotating_equipment=[RotatingEquipment(demand=demand)], mechanical_efficiency=0.95)
        system = SerialEnergySystem(
            nodes=[
                ElectricMotor(efficiency=0.90, max_power_mw=10.0),
                Generator(generator=SimpleFuelConverter(fuel_per_mw=FUEL_PER_MW)),
            ]
        )
        chain = EnergyChain(consumer=shaft, supply_chain=system)

        result = chain.run()

        assert result.fuel.value == (demand / 0.95 / 0.90) * FUEL_PER_MW
        assert result.fuel.energy_type == EnergyType.FUEL
        assert result.demand.value == demand / 0.95
        assert result.demand.energy_type == EnergyType.MECHANICAL
        assert result.capacity_margin_mw == 10.0 - demand / 0.95

    def test_get_all_nodes(self):
        """EnergyChain.get_all_nodes() returns consumer + all supply chain children."""
        shaft = Shaft(rotating_equipment=[RotatingEquipment(demand=1.0)])
        motor = ElectricMotor(efficiency=0.90, max_power_mw=10.0)
        generator = Generator(generator=SimpleFuelConverter(fuel_per_mw=FUEL_PER_MW))
        system = SerialEnergySystem(nodes=[motor, generator])
        chain = EnergyChain(consumer=shaft, supply_chain=system)

        all_nodes = chain.get_all_nodes()

        assert all_nodes[0] is shaft
        assert motor in all_nodes
        assert generator in all_nodes
