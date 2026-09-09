import pytest

from libecalc.energy import ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_network_evaluation import EnergyNetworkEvaluation
from libecalc.energy.energy_units import (
    ElectricalBus,
    ElectricalCable,
    ElectricalConsumer,
    ElectricalMotor,
    ElectricalSource,
    FuelGasSource,
    GeneratorSet,
    MechanicalConsumer,
)
from libecalc.energy.errors import EnergyAllocationRequiredError, InvalidEnergyNetworkEvaluationInputError
from libecalc.energy.network import EnergyConnection, EnergyNetwork


def create_electrical_network():
    source = ElectricalSource("source")
    consumer = ElectricalConsumer("consumer")
    network = EnergyNetwork(
        nodes=[source, consumer],
        connections=[
            EnergyConnection(
                source.get_id(),
                consumer.get_id(),
            ),
        ],
    )
    return network, source, consumer


class TestEnergyNetworkEvaluationInputValidation:
    def test_rejects_missing_consumer_input_energy(self):
        network, _, _ = create_electrical_network()

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="Missing consumer demands for nodes",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                consumer_demands={},
            )

    def test_rejects_consumer_demand_for_non_consumer(self):
        network, source, consumer = create_electrical_network()

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="Unexpected consumer demands for nodes",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                consumer_demands={
                    source.get_id(): ElectricalPower(5),
                    consumer.get_id(): ElectricalPower(5),
                },
            )

    def test_rejects_wrong_consumer_input_energy_type(self):
        network, _, consumer = create_electrical_network()

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="requires ElectricalPower",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                consumer_demands={
                    consumer.get_id(): FuelGasRate(5),
                },
            )


class TestEnergyNetworkEnergyCalculation:
    def test_calculates_input_and_output_energy_through_network(self):
        source = FuelGasSource("source")
        generator = GeneratorSet("generator", max_power=10, power_to_fuel=lambda output: output * 1_000)
        bus = ElectricalBus("bus")
        motor = ElectricalMotor("motor", max_power=10, efficiency=0.8)
        pump = MechanicalConsumer("pump")
        base_load = ElectricalConsumer("base_load")

        network = EnergyNetwork(
            nodes=[source, generator, bus, motor, pump, base_load],
            connections=[
                EnergyConnection(source.get_id(), generator.get_id()),
                EnergyConnection(generator.get_id(), bus.get_id()),
                EnergyConnection(bus.get_id(), motor.get_id()),
                EnergyConnection(motor.get_id(), pump.get_id()),
                EnergyConnection(bus.get_id(), base_load.get_id()),
            ],
        )
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            consumer_demands={
                pump.get_id(): MechanicalPower(4),
                base_load.get_id(): ElectricalPower(5),
            },
        )

        # The pump has 4 MW of mechanical input and no output energy.
        assert evaluation.get_input_energy(pump.get_id()) == MechanicalPower(4)
        assert evaluation.get_output_energy(pump.get_id()) is None

        # The base load has 5 MW of electrical input and no output energy.
        assert evaluation.get_input_energy(base_load.get_id()) == ElectricalPower(5)
        assert evaluation.get_output_energy(base_load.get_id()) is None

        # The motor outputs 4 MW mechanical from 5 MW electrical input.
        assert evaluation.get_input_energy(motor.get_id()) == ElectricalPower(5)
        assert evaluation.get_output_energy(motor.get_id()) == MechanicalPower(4)

        # The bus passes through 10 MW for the motor and base load.
        assert evaluation.get_input_energy(bus.get_id()) == ElectricalPower(10)
        assert evaluation.get_output_energy(bus.get_id()) == ElectricalPower(10)

        # The generator outputs 10 MW from 10,000 Sm3/day of fuel-gas input.
        assert evaluation.get_input_energy(generator.get_id()) == FuelGasRate(10_000)
        assert evaluation.get_output_energy(generator.get_id()) == ElectricalPower(10)

        # The source supplies the generator's total fuel-gas input.
        assert evaluation.get_input_energy(source.get_id()) is None
        assert evaluation.get_output_energy(source.get_id()) == FuelGasRate(10_000)

    def test_returns_typed_zero_output_for_source_without_successors(self):
        source = FuelGasSource("source")
        network = EnergyNetwork(nodes=[source], connections=[])
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            consumer_demands={},
        )

        assert evaluation.get_output_energy(source.get_id()) == FuelGasRate(0)

    def test_requires_allocation_for_multiple_predecessors(self):
        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        load = ElectricalConsumer("load")

        network = EnergyNetwork(
            nodes=[first_grid, second_grid, load],
            connections=[
                EnergyConnection(first_grid.get_id(), load.get_id()),
                EnergyConnection(second_grid.get_id(), load.get_id()),
            ],
        )
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            consumer_demands={
                load.get_id(): ElectricalPower(10),
            },
        )

        with pytest.raises(
            EnergyAllocationRequiredError,
            match="allocation strategy is required",
        ):
            evaluation.get_output_energy(first_grid.get_id())

    def test_does_not_require_allocation_for_zero_energy(self):
        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        load = ElectricalConsumer("load")

        network = EnergyNetwork(
            nodes=[first_grid, second_grid, load],
            connections=[
                EnergyConnection(first_grid.get_id(), load.get_id()),
                EnergyConnection(second_grid.get_id(), load.get_id()),
            ],
        )

        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            consumer_demands={
                load.get_id(): ElectricalPower(0),
            },
        )

        assert evaluation.get_output_energy(first_grid.get_id()) == ElectricalPower(0)

    def test_calculates_input_energy_for_transporter(self):
        source = ElectricalSource("source")
        cable = ElectricalCable("cable", max_power=10, loss_fraction=0.04)
        consumer = ElectricalConsumer("consumer")

        network = EnergyNetwork(
            nodes=[source, cable, consumer],
            connections=[
                EnergyConnection(source.get_id(), cable.get_id()),
                EnergyConnection(cable.get_id(), consumer.get_id()),
            ],
        )

        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            consumer_demands={
                consumer.get_id(): ElectricalPower(10),
            },
        )

        assert evaluation.get_input_energy(cable.get_id()) == ElectricalPower(10 / 0.96)
