"""PowerBus distributes electrical demand across sources by priority."""

from libecalc.domain.energy.network.energy_stream import EnergyStream, EnergyType
from libecalc.domain.energy.network.energy_system import PowerBus
from libecalc.domain.energy.network.nodes.providers import Generator, Shore
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_model import GeneratorSetModel
from libecalc.presentation.yaml.yaml_entities import MemoryResource

FUEL_PER_MW = 100.0  # Sm³/day per MW, from linear generator curve


def _make_generator(max_mw: float) -> Generator:
    """Linear fuel curve: 100 Sm³/day per MW."""
    return Generator(
        generator=GeneratorSetModel(
            name=f"genset_{max_mw}",
            resource=MemoryResource(
                headers=["POWER", "FUEL"],
                data=[[0, max_mw], [0, max_mw * FUEL_PER_MW]],
            ),
        )
    )


class TestPowerBus:
    def test_single_source(self):
        """3 MW demand, single 10 MW generator → 300 Sm³/day fuel."""
        demand = EnergyStream.electrical(3.0)
        result = PowerBus(sources=[_make_generator(10.0)]).supply(demand)
        assert result.energy_type == EnergyType.FUEL
        assert result.value == demand.value * FUEL_PER_MW

    def test_priority_order(self):
        """3 MW demand, two generators — first source covers all demand."""
        demand = EnergyStream.electrical(3.0)
        supply = PowerBus(
            sources=[
                _make_generator(10.0),
                _make_generator(10.0),
            ]
        ).supply(demand)
        assert supply.value == demand.value * FUEL_PER_MW

    def test_spillover_to_second_source(self):
        """3 MW demand, first generator max 2 MW → 1 MW spills to second.

        generator 1: 2 MW × 100 = 200 Sm³/day
        generator 2: 1 MW × 100 = 100 Sm³/day
        """
        demand = EnergyStream.electrical(3.0)
        supply = PowerBus(
            sources=[
                _make_generator(2.0),
                _make_generator(5.0),
            ]
        ).supply(demand)
        assert supply.value == demand.value * FUEL_PER_MW

    def test_generator_plus_shore(self):
        """3 MW demand, generator max 2 MW, shore backup.

        generator: 2 MW × 100 = 200 Sm³/day
        shore: 1 MW → 0 Sm³/day
        """
        demand = EnergyStream.electrical(3.0)
        supply = PowerBus(
            sources=[
                _make_generator(2.0),
                Shore(max_capacity_mw=10.0),
            ]
        ).supply(demand)
        assert supply.value == (demand.value - 1) * FUEL_PER_MW  # Shore covers 1 MW with zero fuel.
