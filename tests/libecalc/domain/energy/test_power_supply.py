"""
Power supplies: take an electrical power demand [MW] and return fuel consumption
and capacity margin. Each implementation models a different source:

- GeneratorSetSupply: fuel-burning generator set (interpolated fuel curve)
- ShoreConnectionSupply: subsea cable from shore (zero fuel, cable loss)
- WindSupply: offshore wind turbine (zero fuel, variable capacity)
"""

import pytest

from libecalc.domain.energy.power_supply.generator_set import GeneratorSetSupply
from libecalc.domain.energy.power_supply.shore import ShoreConnectionResult, ShoreConnectionSupply
from libecalc.domain.energy.power_supply.wind import WindSupply
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_model import GeneratorSetModel
from libecalc.presentation.yaml.yaml_entities import MemoryResource


@pytest.fixture
def generator_set() -> GeneratorSetModel:
    """Max 2 MW, linear fuel curve: 100 Sm³/day per MW."""
    return GeneratorSetModel(
        name="test_genset",
        resource=MemoryResource(
            headers=["POWER", "FUEL"],
            data=[[0, 1, 2], [0, 100, 200]],
        ),
    )


class TestGeneratorSetSupply:
    """Generator set converts power demand to fuel via interpolation."""

    def test_evaluate(self, generator_set):
        """0.5 MW → 50 Sm³/day fuel, 1.5 MW spare capacity."""
        result = GeneratorSetSupply(generator_set=generator_set).evaluate(power_demand_mw=0.5)

        assert result.fuel_rate_sm3_per_day == 50.0
        assert result.power_capacity_margin_mw == 1.5

    def test_exceeds_capacity(self, generator_set):
        """2.5 MW demand on a 2 MW generator → negative capacity margin."""
        result = GeneratorSetSupply(generator_set=generator_set).evaluate(power_demand_mw=2.5)

        assert result.power_capacity_margin_mw < 0


class TestShoreConnectionSupply:
    """Power from shore: zero fuel, but limited by cable capacity and subject to cable losses."""

    def test_no_cable_loss(self):
        """3 MW demand, no losses → 3 MW drawn from shore, 7 MW margin."""
        result = ShoreConnectionSupply(max_capacity_mw=10.0).evaluate(power_demand_mw=3.0)

        assert isinstance(result, ShoreConnectionResult)
        assert result.fuel_rate_sm3_per_day == 0.0
        assert result.power_from_shore_mw == 3.0
        assert result.power_capacity_margin_mw == 7.0

    def test_cable_loss(self):
        """5% cable loss → 3.0 MW platform demand requires 3.15 MW from shore."""
        result = ShoreConnectionSupply(max_capacity_mw=10.0, cable_loss_fraction=0.05).evaluate(power_demand_mw=3.0)

        assert result.power_from_shore_mw == pytest.approx(3.15)
        assert result.power_capacity_margin_mw == pytest.approx(10.0 - 3.15)

    def test_exceeds_capacity_with_cable_loss(self):
        """9.8 MW + 5% loss = 10.29 MW → exceeds 10 MW cable capacity."""
        result = ShoreConnectionSupply(max_capacity_mw=10.0, cable_loss_fraction=0.05).evaluate(power_demand_mw=9.8)

        assert result.power_capacity_margin_mw < 0


class TestWindSupply:
    """Offshore wind: zero fuel, capacity varies with wind conditions."""

    def test_evaluate(self):
        """5 MW available, 3 MW demand → 2 MW margin, no fuel."""
        result = WindSupply(available_power_mw=5.0).evaluate(power_demand_mw=3.0)

        assert result.fuel_rate_sm3_per_day == 0.0
        assert result.power_capacity_margin_mw == 2.0

    def test_variable_capacity(self):
        """Wind drops between timesteps: 5 MW → 2 MW, demand stays at 3 MW."""
        supply = WindSupply(available_power_mw=5.0)
        assert supply.evaluate(power_demand_mw=3.0).power_capacity_margin_mw == 2.0

        supply.set_available_power(2.0)
        assert supply.evaluate(power_demand_mw=3.0).power_capacity_margin_mw == -1.0
