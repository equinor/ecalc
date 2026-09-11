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
from libecalc.energy.errors import InvalidEnergyNetworkEvaluationInputError
from libecalc.energy.network import EnergyNetwork


def create_network(nodes, connections):
    return EnergyNetwork.create(
        node_input_types={node.get_id(): node.get_input_energy_type() for node in nodes},
        node_output_types={node.get_id(): node.get_output_energy_type() for node in nodes},
        connections=connections,
    )


def create_electrical_network():
    source = ElectricalSource("source")
    consumer = ElectricalConsumer("consumer")
    network = create_network(
        nodes=[source, consumer],
        connections=[
            (source.get_id(), consumer.get_id()),
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
            match="Missing connection demands for connections",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                energy_units=[source, consumer],
            ).propagate_energy({})

    def test_rejects_consumer_demand_for_non_consumer(self):
        network, source, consumer = create_electrical_network()

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="Unexpected connection demands for connections",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                energy_units=[source, consumer],
            ).propagate_energy(
                {
                    network.get_connection(source.get_id(), consumer.get_id()).id: ElectricalPower(5),
                    ElectricalSource._create_id(): ElectricalPower(5),
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
                    network.get_connection(source.get_id(), consumer.get_id()).id: FuelGasRate(5),
                }
            )


class TestEnergyNetworkEnergyCalculation:
    def test_calculates_input_and_output_energy_through_network(self):
        source = FuelGasSource("source")
        generator = GeneratorSet("generator", power_to_fuel=lambda output: output * 1_000)
        bus = ElectricalBus("bus")
        motor = ElectricalMotor("motor", efficiency=0.8)
        pump = MechanicalConsumer("pump")
        base_load = ElectricalConsumer("base_load")

        network = create_network(
            nodes=[source, generator, bus, motor, pump, base_load],
            connections=[
                (source.get_id(), generator.get_id()),
                (generator.get_id(), bus.get_id()),
                (bus.get_id(), motor.get_id()),
                (motor.get_id(), pump.get_id()),
                (bus.get_id(), base_load.get_id()),
            ],
        )
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[source, generator, bus, motor, pump, base_load],
        )
        connection_energy = evaluation.propagate_energy(
            {
                network.get_connection(motor.get_id(), pump.get_id()).id: MechanicalPower(4),
                network.get_connection(bus.get_id(), base_load.get_id()).id: ElectricalPower(5),
            }
        )

        assert connection_energy == {
            network.get_connection(source.get_id(), generator.get_id()).id: FuelGasRate(10_000),
            network.get_connection(generator.get_id(), bus.get_id()).id: ElectricalPower(10),
            network.get_connection(bus.get_id(), motor.get_id()).id: ElectricalPower(5),
            network.get_connection(motor.get_id(), pump.get_id()).id: MechanicalPower(4),
            network.get_connection(bus.get_id(), base_load.get_id()).id: ElectricalPower(5),
        }

    def test_returns_no_connection_energy_for_source_without_successors(self):
        source = FuelGasSource("source")
        network = create_network(nodes=[source], connections=[])
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[source],
        )

        assert evaluation.propagate_energy({}) == {}

    def test_propagates_consumer_demands_from_multiple_predecessors(self):
        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        load = ElectricalConsumer("load")

        network = create_network(
            nodes=[first_grid, second_grid, load],
            connections=[
                (first_grid.get_id(), load.get_id()),
                (second_grid.get_id(), load.get_id()),
            ],
        )
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[first_grid, second_grid, load],
        )

        assert evaluation.propagate_energy(
            {
                network.get_connection(first_grid.get_id(), load.get_id()).id: ElectricalPower(4),
                network.get_connection(second_grid.get_id(), load.get_id()).id: ElectricalPower(6),
            }
        ) == {
            network.get_connection(first_grid.get_id(), load.get_id()).id: ElectricalPower(4),
            network.get_connection(second_grid.get_id(), load.get_id()).id: ElectricalPower(6),
        }

    def test_does_not_require_allocation_for_zero_energy(self):
        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        load = ElectricalConsumer("load")

        network = create_network(
            nodes=[first_grid, second_grid, load],
            connections=[
                (first_grid.get_id(), load.get_id()),
                (second_grid.get_id(), load.get_id()),
            ],
        )

        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[first_grid, second_grid, load],
        )

        assert evaluation.propagate_energy(
            {
                network.get_connection(first_grid.get_id(), load.get_id()).id: ElectricalPower(0),
                network.get_connection(second_grid.get_id(), load.get_id()).id: ElectricalPower(0),
            }
        ) == {
            network.get_connection(first_grid.get_id(), load.get_id()).id: ElectricalPower(0),
            network.get_connection(second_grid.get_id(), load.get_id()).id: ElectricalPower(0),
        }

    def test_calculates_input_energy_for_transporter(self):
        source = ElectricalSource("source")
        cable = ElectricalCable("cable", loss_fraction=0.04)
        consumer = ElectricalConsumer("consumer")

        network = create_network(
            nodes=[source, cable, consumer],
            connections=[
                (source.get_id(), cable.get_id()),
                (cable.get_id(), consumer.get_id()),
            ],
        )

        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[source, cable, consumer],
        )

        assert evaluation.propagate_energy(
            {network.get_connection(cable.get_id(), consumer.get_id()).id: ElectricalPower(10)}
        ) == {
            network.get_connection(source.get_id(), cable.get_id()).id: ElectricalPower(10 / 0.96),
            network.get_connection(cable.get_id(), consumer.get_id()).id: ElectricalPower(10),
        }


class TestEnergyNetworkFeasibility:
    def test_reports_capacity_exceeded_without_capping_connection_energy(self):
        grid = ElectricalSource("grid")
        load = ElectricalConsumer("load")
        network = create_network(
            nodes=[grid, load],
            connections=[(grid.get_id(), load.get_id())],
        )
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[grid, load],
        )
        connection = network.get_connection(grid.get_id(), load.get_id())
        connection_energy = evaluation.propagate_energy({connection.id: ElectricalPower(6)})
        capacities = {grid.get_id(): ElectricalPower(5)}

        assert connection_energy[connection.id] == ElectricalPower(6)
        assert evaluation.is_capacity_exceeded(
            node_id=grid.get_id(),
            connection_energy=connection_energy,
            capacities=capacities,
        )

        assert not evaluation.is_feasible(
            connection_energy=connection_energy,
            capacities=capacities,
        )

    def test_capacity_equal_to_connection_energy_is_feasible(self):
        grid = ElectricalSource("grid")
        load = ElectricalConsumer("load")
        network = create_network(
            nodes=[grid, load],
            connections=[(grid.get_id(), load.get_id())],
        )
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[grid, load],
        )
        connection = network.get_connection(grid.get_id(), load.get_id())
        connection_energy = evaluation.propagate_energy({connection.id: ElectricalPower(5)})
        capacities = {grid.get_id(): ElectricalPower(5)}

        assert not evaluation.is_capacity_exceeded(
            node_id=grid.get_id(),
            connection_energy=connection_energy,
            capacities=capacities,
        )
        assert evaluation.is_feasible(
            connection_energy=connection_energy,
            capacities=capacities,
        )

    def test_missing_capacity_means_unlimited(self):
        network, source, consumer = create_electrical_network()
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[source, consumer],
        )
        connection = network.get_connection(source.get_id(), consumer.get_id())
        connection_energy = evaluation.propagate_energy({connection.id: ElectricalPower(5)})
        capacities = {}

        assert not evaluation.is_capacity_exceeded(
            node_id=source.get_id(),
            connection_energy=connection_energy,
            capacities=capacities,
        )
        assert evaluation.is_feasible(
            connection_energy=connection_energy,
            capacities=capacities,
        )

    def test_rejects_capacity_for_consumer(self):
        network, source, consumer = create_electrical_network()
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[source, consumer],
        )
        connection = network.get_connection(source.get_id(), consumer.get_id())
        connection_energy = evaluation.propagate_energy({connection.id: ElectricalPower(5)})

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="Capacity provided for invalid node",
        ):
            evaluation.is_feasible(
                connection_energy=connection_energy,
                capacities={consumer.get_id(): ElectricalPower(10)},
            )

    def test_rejects_wrong_capacity_energy_type(self):
        network, source, consumer = create_electrical_network()
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[source, consumer],
        )
        connection = network.get_connection(source.get_id(), consumer.get_id())
        connection_energy = evaluation.propagate_energy({connection.id: ElectricalPower(5)})

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="must be ElectricalPower",
        ):
            evaluation.is_feasible(
                connection_energy=connection_energy,
                capacities={source.get_id(): FuelGasRate(10)},
            )

    def test_compares_capacity_with_total_outgoing_energy(self):
        grid = ElectricalSource("grid")
        first_load = ElectricalConsumer("first_load")
        second_load = ElectricalConsumer("second_load")
        network = create_network(
            nodes=[grid, first_load, second_load],
            connections=[
                (grid.get_id(), first_load.get_id()),
                (grid.get_id(), second_load.get_id()),
            ],
        )
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[grid, first_load, second_load],
        )
        first_connection = network.get_connection(grid.get_id(), first_load.get_id())
        second_connection = network.get_connection(grid.get_id(), second_load.get_id())
        connection_energy = evaluation.propagate_energy(
            {
                first_connection.id: ElectricalPower(3),
                second_connection.id: ElectricalPower(4),
            }
        )
        capacities = {grid.get_id(): ElectricalPower(6)}

        assert evaluation.is_capacity_exceeded(
            node_id=grid.get_id(),
            connection_energy=connection_energy,
            capacities=capacities,
        )

    def test_validates_all_capacities_before_checking_feasibility(self):
        network, source, consumer = create_electrical_network()
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[source, consumer],
        )
        connection = network.get_connection(source.get_id(), consumer.get_id())
        connection_energy = evaluation.propagate_energy({connection.id: ElectricalPower(5)})

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="Capacity provided for invalid node",
        ):
            evaluation.is_feasible(
                connection_energy=connection_energy,
                capacities={
                    source.get_id(): ElectricalPower(4),
                    consumer.get_id(): ElectricalPower(10),
                },
            )
