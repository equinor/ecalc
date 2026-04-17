"""
Energy chain: rotating equipment → drive train → power supply.

Shows how the three layers compose:
  1. ShaftPowerConsumer computes shaft power from enthalpy rise.
  2. ElectricDriveTrain sums shaft power and applies mechanical losses.
  3. PowerSupply converts the electrical demand into fuel (or not).

The same drive train can be paired with different power supplies —
that's the reason for the separation.
"""

import pytest

from libecalc.domain.energy.drive_train.electric_drive_train import ElectricDriveTrain
from libecalc.domain.energy.power_supply.generator import GeneratorSupply
from libecalc.domain.energy.power_supply.shore import ShoreSupply
from libecalc.domain.energy.rotating_equipment.shaft_power_consumer import ShaftPowerConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_model import GeneratorSetModel
from libecalc.presentation.yaml.yaml_entities import MemoryResource


def _make_drive_train(mechanical_efficiency: float = 1.0) -> ElectricDriveTrain:
    """Two consumers: 0.5 MW + 1.0 MW = 1.5 MW total shaft power.

    Consumer 1: Δh = 50 kJ/kg, ṁ = 36 000 kg/h = 10 kg/s → P = 10 × 50 000 = 500 000 W = 0.5 MW
    Consumer 2: Δh = 100 kJ/kg, ṁ = 36 000 kg/h = 10 kg/s → P = 10 × 100 000 = 1 000 000 W = 1.0 MW
    """
    return ElectricDriveTrain(
        rotating_equipment=[
            ShaftPowerConsumer(
                inlet_enthalpy_joule_per_kg=200_000.0,
                outlet_enthalpy_joule_per_kg=250_000.0,
                mass_rate_kg_per_h=36_000.0,
            ),
            ShaftPowerConsumer(
                inlet_enthalpy_joule_per_kg=100_000.0,
                outlet_enthalpy_joule_per_kg=200_000.0,
                mass_rate_kg_per_h=36_000.0,
            ),
        ],
        mechanical_efficiency=mechanical_efficiency,
    )


@pytest.fixture
def generator_supply() -> GeneratorSupply:
    """Max 5 MW, linear fuel curve: 100 Sm³/day per MW."""
    model = GeneratorSetModel(
        name="test_genset",
        resource=MemoryResource(
            headers=["POWER", "FUEL"],
            data=[[0, 5], [0, 500]],
        ),
    )
    return GeneratorSupply(generator=model)


FUEL_PER_MW = 100.0  # Sm³/day per MW, from the linear curve above


class TestEnergyChain:
    """Full chain: rotating equipment → drive train → power supply."""

    def test_generator_supply(self, generator_supply):
        """1.5 MW electrical demand → generator set → fuel and capacity margin.

        fuel = 1.5 MW × 100 Sm³/day/MW = 150 Sm³/day
        margin = 5.0 MW − 1.5 MW = 3.5 MW
        """
        dt = _make_drive_train()
        result = dt.evaluate()
        power_mw = result.required_electrical_power_mw

        assert power_mw == 1.5

        supply_result = generator_supply.evaluate(power_mw)

        assert supply_result.fuel_rate_sm3_per_day == power_mw * FUEL_PER_MW
        assert supply_result.power_capacity_margin_mw == 5.0 - power_mw

    def test_shore_supply(self):
        """Same drive train, but powered from shore — zero fuel, cable loss reported.

        power_from_shore = 1.5 MW × (1 + 0.05) = 1.575 MW
        margin = 10.0 MW − 1.575 MW = 8.425 MW
        """
        dt = _make_drive_train()
        result = dt.evaluate()
        power_mw = result.required_electrical_power_mw
        cable_loss = 0.05

        supply = ShoreSupply(max_capacity_mw=10.0, cable_loss_fraction=cable_loss)
        supply_result = supply.evaluate(power_mw)

        expected_from_shore = power_mw * (1 + cable_loss)

        assert supply_result.fuel_rate_sm3_per_day == 0.0
        assert supply_result.power_from_shore_mw == expected_from_shore
        assert supply_result.power_capacity_margin_mw == 10.0 - expected_from_shore

    def test_mechanical_efficiency_increases_demand(self, generator_supply):
        """50% mechanical efficiency doubles the electrical demand seen by the power supply.

        shaft = 1.5 MW, electrical = 1.5 / 0.5 = 3.0 MW
        fuel = 3.0 MW × 100 Sm³/day/MW = 300 Sm³/day
        """
        dt = _make_drive_train(mechanical_efficiency=0.5)
        result = dt.evaluate()

        assert result.shaft_power_demand_mw == 1.5
        assert result.required_electrical_power_mw == 3.0

        supply_result = generator_supply.evaluate(result.required_electrical_power_mw)

        assert supply_result.fuel_rate_sm3_per_day == result.required_electrical_power_mw * FUEL_PER_MW

    def test_same_drive_train_different_supplies(self):
        """The same electrical demand can be routed to any PowerSupply."""
        dt = _make_drive_train()
        power_mw = dt.evaluate().required_electrical_power_mw

        generator_supply = GeneratorSupply(
            generator=GeneratorSetModel(
                name="genset",
                resource=MemoryResource(headers=["POWER", "FUEL"], data=[[0, 5], [0, 500]]),
            )
        )
        shore = ShoreSupply(max_capacity_mw=10.0)

        generator_result = generator_supply.evaluate(power_mw)
        shore_result = shore.evaluate(power_mw)

        # Generator set burns fuel
        assert generator_result.fuel_rate_sm3_per_day > 0
        # Shore connection does not
        assert shore_result.fuel_rate_sm3_per_day == 0.0
        # Both report capacity margin
        assert generator_result.power_capacity_margin_mw > 0
        assert shore_result.power_capacity_margin_mw > 0
