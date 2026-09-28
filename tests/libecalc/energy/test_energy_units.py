"""Unit tests for energy_units components."""

from uuid import UUID

import pytest

from libecalc.energy import Consumer, Source
from libecalc.energy.dispatch import PriorityDispatch
from libecalc.energy.energy_network_topology import EnergyConnectionId
from libecalc.energy.energy_types import (
    DieselRate,
    ElectricalPower,
    Energy,
    FuelGasRate,
    MechanicalPower,
)
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import (
    ElectricalBus,
    ElectricalCable,
    ElectricalMotor,
    GasTurbine,
    GeneratorSet,
)

INPUT = EnergyConnectionId(UUID(int=100))
SECOND_INPUT = EnergyConnectionId(UUID(int=101))
FIRST_CANDIDATE = EnergyUnitId(UUID(int=1))
SECOND_CANDIDATE = EnergyUnitId(UUID(int=2))


class TestSources:
    @pytest.mark.parametrize(
        ("source", "expected_output_type"),
        [
            (Source("fuel", output_energy=FuelGasRate(0)), FuelGasRate),
            (Source("diesel", output_energy=DieselRate(0)), DieselRate),
            (Source("electricity", output_energy=ElectricalPower(0)), ElectricalPower),
        ],
    )
    def test_source_energy_contract(
        self,
        source: Source,
        expected_output_type: type[Energy],
    ):
        assert source.get_input_energy_type() is None
        assert source.get_output_energy_type() is expected_output_type
        assert source.get_input_energies() == {}
        assert isinstance(source.get_id(), UUID)


class TestConverters:
    def test_electrical_cable_accounts_for_loss(self):
        cable = ElectricalCable(
            "cable", output_energy=ElectricalPower(10.0), input_connection_id=INPUT, loss_fraction=0.04
        )
        result = cable.get_input_energies()
        assert result.keys() == {INPUT}
        assert result[INPUT].value == pytest.approx(10.0 / 0.96)

    def test_generator_set_applies_fuel_curve(self):
        genset = GeneratorSet(
            "gs1",
            output_energy=ElectricalPower(10.0),
            input_connection_id=INPUT,
            power_to_fuel=lambda mw: 5000 + mw * 4500,
        )
        assert genset.get_input_energies() == {INPUT: FuelGasRate(5000 + 10 * 4500)}

    def test_gas_turbine_applies_fuel_curve(self):
        turbine = GasTurbine(
            "t1",
            output_energy=MechanicalPower(15.0),
            input_connection_id=INPUT,
            power_to_fuel=lambda mw: 3000 + mw * 3500,
        )
        assert turbine.get_input_energies() == {INPUT: FuelGasRate(3000 + 15 * 3500)}

    def test_electrical_motor_divides_by_efficiency(self):
        motor = ElectricalMotor("m1", output_energy=MechanicalPower(7.0), input_connection_id=INPUT, efficiency=0.93)
        result = motor.get_input_energies()
        assert result.keys() == {INPUT}
        assert result[INPUT].value == pytest.approx(7.0 / 0.93)
        assert isinstance(result[INPUT], ElectricalPower)


class TestConsumers:
    @pytest.mark.parametrize(
        ("consumer", "expected_input_type"),
        [
            (
                Consumer("electrical_consumer", demand=ElectricalPower(3), input_connection_id=INPUT),
                ElectricalPower,
            ),
            (
                Consumer("compressor", demand=MechanicalPower(3), input_connection_id=INPUT),
                MechanicalPower,
            ),
            (Consumer("diesel_consumer", demand=DieselRate(3), input_connection_id=INPUT), DieselRate),
            (Consumer("fuel_consumer", demand=FuelGasRate(3), input_connection_id=INPUT), FuelGasRate),
        ],
    )
    def test_consumer_energy_contract(
        self,
        consumer: Consumer,
        expected_input_type: type[Energy],
    ):
        assert consumer.get_input_energy_type() is expected_input_type
        assert consumer.get_output_energy_type() is None
        assert consumer.get_input_energies() == {INPUT: expected_input_type(3)}
        assert isinstance(consumer.get_id(), UUID)


class TestJunctions:
    def test_places_demand_beyond_every_limit_on_the_last_input(self):
        bus = ElectricalBus(
            "bus",
            output_energy=ElectricalPower(10),
            input_connection_ids={FIRST_CANDIDATE: INPUT, SECOND_CANDIDATE: SECOND_INPUT},
            dispatch_strategy=PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE)),
            input_capacities={FIRST_CANDIDATE: ElectricalPower(4), SECOND_CANDIDATE: ElectricalPower(3)},
        )

        assert bus.get_input_energies() == {INPUT: ElectricalPower(4), SECOND_INPUT: ElectricalPower(6)}
        assert bus.get_failures() == []
