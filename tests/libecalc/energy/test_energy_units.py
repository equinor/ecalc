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
            (FuelGasSource("fuel", output_energy=FuelGasRate(0)), FuelGasRate),
            (DieselSource("diesel", output_energy=DieselRate(0)), DieselRate),
            (ElectricalSource("electricity", output_energy=ElectricalPower(0)), ElectricalPower),
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
        cable = ElectricalCable("cable", output_energy=ElectricalPower(10.0), loss_fraction=0.04)
        result = cable.get_input_energy()
        assert result.value == pytest.approx(10.0 / 0.96)

    def test_generator_set_applies_fuel_curve(self):
        genset = GeneratorSet("gs1", output_energy=ElectricalPower(10.0), power_to_fuel=lambda mw: 5000 + mw * 4500)
        result = genset.get_input_energy()
        assert result == FuelGasRate(5000 + 10 * 4500)

    def test_gas_turbine_applies_fuel_curve(self):
        turbine = GasTurbine("t1", output_energy=MechanicalPower(15.0), power_to_fuel=lambda mw: 3000 + mw * 3500)
        result = turbine.get_input_energy()
        assert result == FuelGasRate(3000 + 15 * 3500)

    def test_electrical_motor_divides_by_efficiency(self):
        motor = ElectricalMotor("m1", output_energy=MechanicalPower(7.0), efficiency=0.93)
        result = motor.get_input_energy()
        assert result.value == pytest.approx(7.0 / 0.93)
        assert isinstance(result, ElectricalPower)


class TestConsumers:
    @pytest.mark.parametrize(
        ("consumer", "expected_input_type"),
        [
            (ElectricalConsumer("electrical_consumer", demand=ElectricalPower(0)), ElectricalPower),
            (MechanicalConsumer("compressor", demand=MechanicalPower(0)), MechanicalPower),
            (DieselConsumer("diesel_consumer", demand=DieselRate(0)), DieselRate),
            (FuelGasConsumer("fuel_consumer", demand=FuelGasRate(0)), FuelGasRate),
        ],
    )
    def test_consumer_energy_contract(
        self,
        consumer: Consumer,
        expected_input_type: type[Energy],
    ):
        assert consumer.get_input_energy_type() is expected_input_type
        assert consumer.get_output_energy_type() is None
        assert consumer.get_demand() == expected_input_type(0)
        assert isinstance(consumer.get_id(), UUID)
