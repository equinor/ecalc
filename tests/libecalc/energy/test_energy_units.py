"""Unit tests for energy_units components."""

from uuid import UUID

import pytest

from libecalc.energy import Consumer, Source
from libecalc.energy.energy_types import (
    DieselRate,
    ElectricalPower,
    Energy,
    FuelGasRate,
    MechanicalPower,
)
from libecalc.energy.energy_units import (
    DieselConsumer,
    DieselSource,
    ElectricalCable,
    ElectricalConsumer,
    ElectricalMotor,
    ElectricalSource,
    FuelGasConsumer,
    FuelGasSource,
    GasTurbine,
    GeneratorSet,
    MechanicalConsumer,
)


class TestSources:
    @pytest.mark.parametrize(
        ("source", "expected_output_type"),
        [
            (FuelGasSource("fuel"), FuelGasRate),
            (DieselSource("diesel"), DieselRate),
            (ElectricalSource("electricity"), ElectricalPower),
        ],
    )
    def test_source_energy_contract(
        self,
        source: Source,
        expected_output_type: type[Energy],
    ):
        assert source.get_input_energy_type() is None
        assert source.get_output_energy_type() is expected_output_type
        assert isinstance(source.get_id(), UUID)


class TestConverters:
    def test_electrical_cable_accounts_for_loss(self):
        cable = ElectricalCable("cable", loss_fraction=0.04)
        result = cable.get_input_energy(ElectricalPower(10.0))
        assert result.value == pytest.approx(10.0 / 0.96)

    def test_generator_set_applies_fuel_curve(self):
        genset = GeneratorSet("gs1", power_to_fuel=lambda mw: 5000 + mw * 4500)
        result = genset.get_input_energy(ElectricalPower(10.0))
        assert result == FuelGasRate(5000 + 10 * 4500)

    def test_gas_turbine_applies_fuel_curve(self):
        turbine = GasTurbine("t1", power_to_fuel=lambda mw: 3000 + mw * 3500)
        result = turbine.get_input_energy(MechanicalPower(15.0))
        assert result == FuelGasRate(3000 + 15 * 3500)

    def test_electrical_motor_divides_by_efficiency(self):
        motor = ElectricalMotor("m1", efficiency=0.93)
        result = motor.get_input_energy(MechanicalPower(7.0))
        assert result.value == pytest.approx(7.0 / 0.93)
        assert isinstance(result, ElectricalPower)


class TestConsumers:
    @pytest.mark.parametrize(
        ("consumer", "expected_input_type"),
        [
            (ElectricalConsumer("electrical_consumer"), ElectricalPower),
            (MechanicalConsumer("compressor"), MechanicalPower),
            (DieselConsumer("diesel_consumer"), DieselRate),
            (FuelGasConsumer("fuel_consumer"), FuelGasRate),
        ],
    )
    def test_consumer_energy_contract(
        self,
        consumer: Consumer,
        expected_input_type: type[Energy],
    ):
        assert consumer.get_input_energy_type() is expected_input_type
        assert consumer.get_output_energy_type() is None
        assert isinstance(consumer.get_id(), UUID)
