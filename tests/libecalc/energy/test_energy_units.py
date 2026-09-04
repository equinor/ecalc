"""Unit tests for energy_units components."""

from uuid import UUID

import pytest

from libecalc.energy import Consumer
from libecalc.energy.energy_types import (
    DieselRate,
    ElectricalPower,
    Energy,
    FuelGasRate,
    MechanicalPower,
)
from libecalc.energy.energy_units import (
    DieselConsumer,
    ElectricalCable,
    ElectricalConsumer,
    ElectricalMotor,
    FuelGasConsumer,
    FuelGasSource,
    GasTurbine,
    GeneratorSet,
    MechanicalConsumer,
)


class TestSources:
    def test_capped_source_reports_capacity(self):
        src = FuelGasSource("fg", max_rate=100_000.0)
        assert src.capacity() == FuelGasRate(100_000.0)

    def test_uncapped_source_has_no_limit(self):
        src = FuelGasSource("fg")
        assert src.capacity() is None


class TestConverters:
    def test_electrical_cable_accounts_for_loss(self):
        cable = ElectricalCable("cable", max_power=45.0, loss_fraction=0.04)
        result = cable.get_input_energy(ElectricalPower(10.0))
        assert result.value == pytest.approx(10.0 / 0.96)
        assert cable.capacity() == ElectricalPower(45.0)

    def test_generator_set_applies_fuel_curve(self):
        genset = GeneratorSet("gs1", max_power=20.0, power_to_fuel=lambda mw: 5000 + mw * 4500)
        result = genset.get_energy_demand(ElectricalPower(10.0))
        assert result == FuelGasRate(5000 + 10 * 4500)
        assert genset.capacity() == ElectricalPower(20.0)

    def test_gas_turbine_applies_fuel_curve(self):
        turbine = GasTurbine("t1", max_power=25.0, power_to_fuel=lambda mw: 3000 + mw * 3500)
        result = turbine.get_energy_demand(MechanicalPower(15.0))
        assert result == FuelGasRate(3000 + 15 * 3500)
        assert turbine.capacity() == MechanicalPower(25.0)

    def test_electrical_motor_divides_by_efficiency(self):
        motor = ElectricalMotor("m1", max_power=8.0, efficiency=0.93)
        result = motor.get_energy_demand(MechanicalPower(7.0))
        assert result.value == pytest.approx(7.0 / 0.93)
        assert isinstance(result, ElectricalPower)
        assert motor.capacity() == MechanicalPower(8.0)


class TestConsumers:
    @pytest.mark.parametrize(
        ("consumer", "expected_energy"),
        [
            (ElectricalConsumer("electrical_consumer", power=1.5), ElectricalPower(1.5)),
            (MechanicalConsumer("compressor", power=2), MechanicalPower(2)),
            (DieselConsumer("diesel_consumer", rate=500.0), DieselRate(500.0)),
            (FuelGasConsumer("fuel_consumer", rate=1_000), FuelGasRate(1_000)),
        ],
    )
    def test_consumer_returns_input_energy(self, consumer: Consumer, expected_energy: Energy):
        assert consumer.get_input_energy() == expected_energy
        assert isinstance(consumer.get_id(), UUID)
