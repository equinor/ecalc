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
from libecalc.energy.network_unit import EnergyNetworkUnit


def create_electrical_network():
    source = ElectricalSource("source")
    consumer = ElectricalConsumer("consumer")
    network_source = EnergyNetworkUnit("source", None, ElectricalPower, source.get_id())
    network_consumer = EnergyNetworkUnit("consumer", ElectricalPower, None, consumer.get_id())
    network = EnergyNetwork(
        nodes=[network_source, network_consumer],
        connections=[
            EnergyConnection(
                source.get_id(),
                consumer.get_id(),
            ),
        ],
    )
    return network, source, consumer


class TestEnergyNetworkEvaluationInputValidation:
    def test_rejects_energy_units_with_different_energy_types_than_network(self):
        network, source, consumer = create_electrical_network()
        incompatible_consumer = MechanicalConsumer("consumer", energy_unit_id=consumer.get_id())

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="energy types that do not match the network",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                energy_units=[source, incompatible_consumer],
            )

    def test_rejects_missing_consumer_input_energy(self):
        network, source, consumer = create_electrical_network()

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="Missing consumer demands for nodes",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                energy_units=[source, consumer],
            ).propagate_energy({})

    def test_rejects_consumer_demand_for_non_consumer(self):
        network, source, consumer = create_electrical_network()

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="Unexpected consumer demands for nodes",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                energy_units=[source, consumer],
            ).propagate_energy(
                {
                    source.get_id(): ElectricalPower(5),
                    consumer.get_id(): ElectricalPower(5),
                }
            )

    def test_rejects_wrong_consumer_input_energy_type(self):
        network, source, consumer = create_electrical_network()

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="requires ElectricalPower",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                energy_units=[source, consumer],
            ).propagate_energy(
                {
                    consumer.get_id(): FuelGasRate(5),
                }
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
            energy_units=[source, generator, bus, motor, pump, base_load],
        )
        connection_energy = evaluation.propagate_energy(
            {
                pump.get_id(): MechanicalPower(4),
                base_load.get_id(): ElectricalPower(5),
            }
        )

        assert connection_energy == {
            EnergyConnection(source.get_id(), generator.get_id()): FuelGasRate(10_000),
            EnergyConnection(generator.get_id(), bus.get_id()): ElectricalPower(10),
            EnergyConnection(bus.get_id(), motor.get_id()): ElectricalPower(5),
            EnergyConnection(motor.get_id(), pump.get_id()): MechanicalPower(4),
            EnergyConnection(bus.get_id(), base_load.get_id()): ElectricalPower(5),
        }

    def test_returns_no_connection_energy_for_source_without_successors(self):
        source = FuelGasSource("source")
        network = EnergyNetwork(nodes=[source], connections=[])
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[source],
        )

        assert evaluation.propagate_energy({}) == {}

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
            energy_units=[first_grid, second_grid, load],
        )

        with pytest.raises(
            EnergyAllocationRequiredError,
            match="allocation strategy is required",
        ):
            evaluation.propagate_energy({load.get_id(): ElectricalPower(10)})

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
            energy_units=[first_grid, second_grid, load],
        )

        assert evaluation.propagate_energy({load.get_id(): ElectricalPower(0)}) == {
            EnergyConnection(first_grid.get_id(), load.get_id()): ElectricalPower(0),
            EnergyConnection(second_grid.get_id(), load.get_id()): ElectricalPower(0),
        }

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
            energy_units=[source, cable, consumer],
        )

        assert evaluation.propagate_energy({consumer.get_id(): ElectricalPower(10)}) == {
            EnergyConnection(source.get_id(), cable.get_id()): ElectricalPower(10 / 0.96),
            EnergyConnection(cable.get_id(), consumer.get_id()): ElectricalPower(10),
        }
