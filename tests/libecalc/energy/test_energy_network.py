from typing import cast

import pytest

from libecalc.energy import (
    CapacityFailure,
    ElectricalPower,
    EnergyFailureStatus,
    EnergyUnitId,
    FuelGasRate,
    MechanicalPower,
)
from libecalc.energy.dispatch import PriorityDispatch
from libecalc.energy.energy_network import EnergyNetwork
from libecalc.energy.energy_network_topology import EnergyConnectionId, EnergyNetworkTopology
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
from libecalc.energy.errors import (
    EnergyAllocationRequiredError,
    InvalidEnergyNetworkError,
    InvalidEnergyNetworkInputError,
)


def create_topology(nodes, connections):
    return EnergyNetworkTopology.create(
        node_input_types={node.get_id(): node.get_input_energy_type() for node in nodes},
        node_output_types={node.get_id(): node.get_output_energy_type() for node in nodes},
        connections=connections,
    )


def create_electrical_topology():
    source = ElectricalSource("source")
    consumer = ElectricalConsumer("consumer")
    topology = create_topology(
        nodes=[source, consumer],
        connections=[
            (source.get_id(), consumer.get_id()),
        ],
    )
    return topology, source, consumer


class TestEnergyNetworkInputValidation:
    def test_rejects_energy_units_with_different_energy_types_than_network(self):
        topology, source, consumer = create_electrical_topology()
        incompatible_consumer = MechanicalConsumer("consumer", energy_unit_id=consumer.get_id())

        with pytest.raises(
            InvalidEnergyNetworkInputError,
            match="energy types that do not match the network",
        ):
            EnergyNetwork(
                topology=topology,
                energy_units=[source, incompatible_consumer],
            )

    def test_rejects_missing_consumer_input_energy(self):
        topology, source, consumer = create_electrical_topology()

        with pytest.raises(
            InvalidEnergyNetworkInputError,
            match=r"Missing connection demands for connections: 'source'.*-> 'consumer'",
        ):
            EnergyNetwork(
                topology=topology,
                energy_units=[source, consumer],
            ).propagate_energy({})

    def test_rejects_consumer_demand_for_non_consumer(self):
        topology, source, consumer = create_electrical_topology()

        with pytest.raises(
            InvalidEnergyNetworkInputError,
            match="Unexpected connection demands for connections",
        ):
            EnergyNetwork(
                topology=topology,
                energy_units=[source, consumer],
            ).propagate_energy(
                {
                    topology.get_connection(source.get_id(), consumer.get_id()).id: ElectricalPower(5),
                    cast(EnergyConnectionId, ElectricalSource._create_id()): ElectricalPower(5),
                }
            )

    def test_rejects_wrong_consumer_input_energy_type(self):
        topology, source, consumer = create_electrical_topology()

        with pytest.raises(
            InvalidEnergyNetworkInputError,
            match=r"Consumer demand for connection 'source'.*-> 'consumer'.*requires ElectricalPower",
        ):
            EnergyNetwork(
                topology=topology,
                energy_units=[source, consumer],
            ).propagate_energy(
                {
                    topology.get_connection(source.get_id(), consumer.get_id()).id: FuelGasRate(5),
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

        topology = create_topology(
            nodes=[source, generator, bus, motor, pump, base_load],
            connections=[
                (source.get_id(), generator.get_id()),
                (generator.get_id(), bus.get_id()),
                (bus.get_id(), motor.get_id()),
                (motor.get_id(), pump.get_id()),
                (bus.get_id(), base_load.get_id()),
            ],
        )
        network = EnergyNetwork(
            topology=topology,
            energy_units=[source, generator, bus, motor, pump, base_load],
        )
        propagation = network.propagate_energy(
            {
                topology.get_connection(motor.get_id(), pump.get_id()).id: MechanicalPower(4),
                topology.get_connection(bus.get_id(), base_load.get_id()).id: ElectricalPower(5),
            }
        )

        assert {connection_id: connection.energy for connection_id, connection in propagation.connections.items()} == {
            topology.get_connection(source.get_id(), generator.get_id()).id: FuelGasRate(10_000),
            topology.get_connection(generator.get_id(), bus.get_id()).id: ElectricalPower(10),
            topology.get_connection(bus.get_id(), motor.get_id()).id: ElectricalPower(5),
            topology.get_connection(motor.get_id(), pump.get_id()).id: MechanicalPower(4),
            topology.get_connection(bus.get_id(), base_load.get_id()).id: ElectricalPower(5),
        }
        assert not propagation.capacity_failures

    def test_returns_no_connection_energy_for_source_without_successors(self):
        source = FuelGasSource("source")
        topology = create_topology(nodes=[source], connections=[])
        network = EnergyNetwork(
            topology=topology,
            energy_units=[source],
        )

        propagation = network.propagate_energy({})

        assert not propagation.connections
        assert not propagation.capacity_failures

    def test_calculates_input_energy_for_transporter(self):
        source = ElectricalSource("source")
        cable = ElectricalCable("cable", loss_fraction=0.04)
        consumer = ElectricalConsumer("consumer")

        topology = create_topology(
            nodes=[source, cable, consumer],
            connections=[
                (source.get_id(), cable.get_id()),
                (cable.get_id(), consumer.get_id()),
            ],
        )

        network = EnergyNetwork(
            topology=topology,
            energy_units=[source, cable, consumer],
        )

        propagation = network.propagate_energy(
            {topology.get_connection(cable.get_id(), consumer.get_id()).id: ElectricalPower(10)}
        )

        assert {connection_id: connection.energy for connection_id, connection in propagation.connections.items()} == {
            topology.get_connection(source.get_id(), cable.get_id()).id: ElectricalPower(10 / 0.96),
            topology.get_connection(cable.get_id(), consumer.get_id()).id: ElectricalPower(10),
        }
        assert not propagation.capacity_failures


class TestEnergyNetworkCapacity:
    def test_reports_capacity_exceeded_without_capping_connection_energy(self):
        grid = ElectricalSource("grid")
        load = ElectricalConsumer("load")
        topology = create_topology(
            nodes=[grid, load],
            connections=[(grid.get_id(), load.get_id())],
        )
        network = EnergyNetwork(
            topology=topology,
            energy_units=[grid, load],
        )
        connection = topology.get_connection(grid.get_id(), load.get_id())
        capacities = {grid.get_id(): ElectricalPower(5)}
        propagation = network.propagate_energy(
            {connection.id: ElectricalPower(6)},
            capacities=capacities,
        )

        assert propagation.connections[connection.id].energy == ElectricalPower(6)
        assert set(propagation.capacity_failures) == {grid.get_id()}
        assert isinstance(propagation.capacity_failures[grid.get_id()], CapacityFailure)
        assert propagation.capacity_failures[grid.get_id()].status == EnergyFailureStatus.CAPACITY_EXCEEDED
        assert propagation.capacity_failures[grid.get_id()].energy_unit_id == grid.get_id()
        assert propagation.capacity_failures[grid.get_id()].required_energy == ElectricalPower(6)
        assert propagation.capacity_failures[grid.get_id()].capacity == ElectricalPower(5)
        assert not propagation.connections[connection.id].affected_by

    def test_capacity_equal_to_connection_energy_has_no_failure(self):
        grid = ElectricalSource("grid")
        load = ElectricalConsumer("load")
        topology = create_topology(
            nodes=[grid, load],
            connections=[(grid.get_id(), load.get_id())],
        )
        network = EnergyNetwork(
            topology=topology,
            energy_units=[grid, load],
        )
        connection = topology.get_connection(grid.get_id(), load.get_id())
        capacities = {grid.get_id(): ElectricalPower(5)}
        propagation = network.propagate_energy(
            {connection.id: ElectricalPower(5)},
            capacities=capacities,
        )

        assert not propagation.capacity_failures

    def test_missing_capacity_means_unlimited(self):
        topology, source, consumer = create_electrical_topology()
        network = EnergyNetwork(
            topology=topology,
            energy_units=[source, consumer],
        )
        connection = topology.get_connection(source.get_id(), consumer.get_id())
        propagation = network.propagate_energy({connection.id: ElectricalPower(5)})

        assert not propagation.capacity_failures

    def test_marks_connections_towards_source_as_affected_by_capacity_failure(self):
        source = ElectricalSource("source")
        upstream_cable = ElectricalCable("upstream_cable", loss_fraction=0)
        constrained_cable = ElectricalCable("constrained_cable", loss_fraction=0)
        load = ElectricalConsumer("load")
        topology = create_topology(
            nodes=[source, upstream_cable, constrained_cable, load],
            connections=[
                (source.get_id(), upstream_cable.get_id()),
                (upstream_cable.get_id(), constrained_cable.get_id()),
                (constrained_cable.get_id(), load.get_id()),
            ],
        )
        network = EnergyNetwork(
            topology=topology,
            energy_units=[source, upstream_cable, constrained_cable, load],
        )
        source_connection = topology.get_connection(source.get_id(), upstream_cable.get_id())
        constrained_connection = topology.get_connection(upstream_cable.get_id(), constrained_cable.get_id())
        load_connection = topology.get_connection(constrained_cable.get_id(), load.get_id())

        propagation = network.propagate_energy(
            {load_connection.id: ElectricalPower(6)},
            capacities={
                source.get_id(): ElectricalPower(10),
                constrained_cable.get_id(): ElectricalPower(5),
            },
        )

        # The local failure affects only predecessor connections and does not change their required energy.
        assert set(propagation.capacity_failures) == {constrained_cable.get_id()}
        assert propagation.connections[source_connection.id].energy == ElectricalPower(6)
        failure = propagation.capacity_failures[constrained_cable.get_id()]
        assert propagation.connections[source_connection.id].affected_by == (failure,)
        assert propagation.connections[constrained_connection.id].affected_by == (failure,)
        assert not propagation.connections[load_connection.id].affected_by

    def test_connection_can_be_affected_by_multiple_capacity_failures(self):
        source = ElectricalSource("source")
        bus = ElectricalBus("bus")
        first_cable = ElectricalCable("first_cable", loss_fraction=0)
        second_cable = ElectricalCable("second_cable", loss_fraction=0)
        first_load = ElectricalConsumer("first_load")
        second_load = ElectricalConsumer("second_load")
        units = [source, bus, first_cable, second_cable, first_load, second_load]
        topology = create_topology(
            nodes=units,
            connections=[
                (source.get_id(), bus.get_id()),
                (bus.get_id(), first_cable.get_id()),
                (bus.get_id(), second_cable.get_id()),
                (first_cable.get_id(), first_load.get_id()),
                (second_cable.get_id(), second_load.get_id()),
            ],
        )
        network = EnergyNetwork(topology=topology, energy_units=units)
        source_connection = topology.get_connection(source.get_id(), bus.get_id())

        propagation = network.propagate_energy(
            {
                topology.get_connection(first_cable.get_id(), first_load.get_id()).id: ElectricalPower(6),
                topology.get_connection(second_cable.get_id(), second_load.get_id()).id: ElectricalPower(7),
            },
            capacities={
                first_cable.get_id(): ElectricalPower(5),
                second_cable.get_id(): ElectricalPower(6),
            },
        )

        # Both downstream failures affect the connection shared on their paths towards the source.
        affected_unit_ids: set[EnergyUnitId] = set()
        for failure in propagation.connections[source_connection.id].affected_by:
            assert isinstance(failure, CapacityFailure)
            affected_unit_ids.add(failure.energy_unit_id)

        assert affected_unit_ids == {
            first_cable.get_id(),
            second_cable.get_id(),
        }

    def test_rejects_capacity_for_consumer(self):
        topology, source, consumer = create_electrical_topology()
        network = EnergyNetwork(
            topology=topology,
            energy_units=[source, consumer],
        )
        connection = topology.get_connection(source.get_id(), consumer.get_id())

        with pytest.raises(
            InvalidEnergyNetworkInputError,
            match="Capacity provided for invalid node",
        ):
            network.propagate_energy(
                {connection.id: ElectricalPower(5)},
                capacities={consumer.get_id(): ElectricalPower(10)},
            )

    def test_rejects_wrong_capacity_energy_type(self):
        topology, source, consumer = create_electrical_topology()
        network = EnergyNetwork(
            topology=topology,
            energy_units=[source, consumer],
        )
        connection = topology.get_connection(source.get_id(), consumer.get_id())

        with pytest.raises(
            InvalidEnergyNetworkInputError,
            match="must be ElectricalPower",
        ):
            network.propagate_energy(
                {connection.id: ElectricalPower(5)},
                capacities={source.get_id(): FuelGasRate(10)},
            )

    def test_compares_capacity_with_total_outgoing_energy(self):
        grid = ElectricalSource("grid")
        first_load = ElectricalConsumer("first_load")
        second_load = ElectricalConsumer("second_load")
        topology = create_topology(
            nodes=[grid, first_load, second_load],
            connections=[
                (grid.get_id(), first_load.get_id()),
                (grid.get_id(), second_load.get_id()),
            ],
        )
        network = EnergyNetwork(
            topology=topology,
            energy_units=[grid, first_load, second_load],
        )
        first_connection = topology.get_connection(grid.get_id(), first_load.get_id())
        second_connection = topology.get_connection(grid.get_id(), second_load.get_id())
        capacities = {grid.get_id(): ElectricalPower(6)}
        propagation = network.propagate_energy(
            {
                first_connection.id: ElectricalPower(3),
                second_connection.id: ElectricalPower(4),
            },
            capacities=capacities,
        )
        assert propagation.capacity_failures[grid.get_id()].status == EnergyFailureStatus.CAPACITY_EXCEEDED

    def test_validates_all_capacities_before_propagating_energy(self):
        topology, source, consumer = create_electrical_topology()
        network = EnergyNetwork(
            topology=topology,
            energy_units=[source, consumer],
        )
        connection = topology.get_connection(source.get_id(), consumer.get_id())

        with pytest.raises(
            InvalidEnergyNetworkInputError,
            match="Capacity provided for invalid node",
        ):
            network.propagate_energy(
                {connection.id: ElectricalPower(5)},
                capacities={
                    source.get_id(): ElectricalPower(4),
                    consumer.get_id(): ElectricalPower(10),
                },
            )


class TestJunctionDispatch:
    def test_dispatches_to_shore_before_genset(self):
        """Power from shore is filled first, and the generator set covers only the shortfall."""
        fuel_source = FuelGasSource("fuel_source")
        grid = ElectricalSource("grid")
        genset = GeneratorSet("genset", power_to_fuel=lambda power: power * 1_000)
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(grid.get_id(), genset.get_id())))
        load = ElectricalConsumer("load")

        units = [fuel_source, grid, genset, bus, load]
        topology = create_topology(
            nodes=units,
            connections=[
                (fuel_source.get_id(), genset.get_id()),
                (grid.get_id(), bus.get_id()),
                (genset.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        network = EnergyNetwork(topology=topology, energy_units=units)

        propagation = network.propagate_energy(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(8)},
            capacities={grid.get_id(): ElectricalPower(5), genset.get_id(): ElectricalPower(10)},
        )

        assert propagation.connections[
            topology.get_connection(grid.get_id(), bus.get_id()).id
        ].energy == ElectricalPower(5)
        assert propagation.connections[
            topology.get_connection(genset.get_id(), bus.get_id()).id
        ].energy == ElectricalPower(3)
        assert propagation.connections[
            topology.get_connection(fuel_source.get_id(), genset.get_id()).id
        ].energy == FuelGasRate(3_000)
        assert not propagation.capacity_failures

    def test_separate_genset_curves_reproduce_legacy_fuel_jump(self):
        """Per-generator curves replace the jumps encoded in a single legacy curve."""
        fuel_source = FuelGasSource("fuel_source")
        first = GeneratorSet("first_genset", power_to_fuel=lambda power: power * 1_000)
        second = GeneratorSet("second_genset", power_to_fuel=lambda power: 10_000 + power * 2_000)
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(first.get_id(), second.get_id())))
        load = ElectricalConsumer("load")

        units = [fuel_source, first, second, bus, load]
        topology = create_topology(
            nodes=units,
            connections=[
                (fuel_source.get_id(), first.get_id()),
                (fuel_source.get_id(), second.get_id()),
                (first.get_id(), bus.get_id()),
                (second.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        network = EnergyNetwork(topology=topology, energy_units=units)

        propagation = network.propagate_energy(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(12)},
            capacities={first.get_id(): ElectricalPower(10), second.get_id(): ElectricalPower(10)},
        )

        assert propagation.connections[
            topology.get_connection(first.get_id(), bus.get_id()).id
        ].energy == ElectricalPower(10)
        assert propagation.connections[
            topology.get_connection(second.get_id(), bus.get_id()).id
        ].energy == ElectricalPower(2)
        assert propagation.connections[
            topology.get_connection(fuel_source.get_id(), first.get_id()).id
        ].energy == FuelGasRate(10_000)
        assert propagation.connections[
            topology.get_connection(fuel_source.get_id(), second.get_id()).id
        ].energy == FuelGasRate(14_000)
        assert not propagation.capacity_failures

    def test_overflows_last_candidate_when_total_capacity_is_insufficient(self):
        """Demand beyond total capacity lands on the last candidate rather than raising."""
        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        bus = ElectricalBus(
            "bus", dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), second_grid.get_id()))
        )
        load = ElectricalConsumer("load")

        units = [first_grid, second_grid, bus, load]
        topology = create_topology(
            nodes=units,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        network = EnergyNetwork(topology=topology, energy_units=units)

        capacities = {first_grid.get_id(): ElectricalPower(5), second_grid.get_id(): ElectricalPower(5)}
        propagation = network.propagate_energy(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(12)},
            capacities=capacities,
        )

        assert propagation.connections[
            topology.get_connection(first_grid.get_id(), bus.get_id()).id
        ].energy == ElectricalPower(5)
        assert propagation.connections[
            topology.get_connection(second_grid.get_id(), bus.get_id()).id
        ].energy == ElectricalPower(7)

        # The overflow is reported rather than raised: the second grid is over its rating.
        assert set(propagation.capacity_failures) == {second_grid.get_id()}
        assert propagation.capacity_failures[second_grid.get_id()].status == EnergyFailureStatus.CAPACITY_EXCEEDED

    def test_dispatch_uses_cable_capacity_not_upstream_grid_capacity(self):
        """Availability is a candidate's own capacity, not what the chain behind it can deliver."""
        grid = ElectricalSource("grid")
        cable = ElectricalCable("cable")
        wind = ElectricalSource("wind")
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(cable.get_id(), wind.get_id())))
        load = ElectricalConsumer("load")

        units = [grid, cable, wind, bus, load]
        topology = create_topology(
            nodes=units,
            connections=[
                (grid.get_id(), cable.get_id()),
                (cable.get_id(), bus.get_id()),
                (wind.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        network = EnergyNetwork(topology=topology, energy_units=units)

        capacities = {
            grid.get_id(): ElectricalPower(20),
            cable.get_id(): ElectricalPower(30),
            wind.get_id(): ElectricalPower(10),
        }
        propagation = network.propagate_energy(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(25)},
            capacities=capacities,
        )

        # The cable is filled to its own 30 MW rating, so the 20 MW grid behind it is over-drawn
        # and the 10 MW wind source is left idle.
        assert propagation.connections[
            topology.get_connection(cable.get_id(), bus.get_id()).id
        ].energy == ElectricalPower(25)
        assert propagation.connections[
            topology.get_connection(grid.get_id(), cable.get_id()).id
        ].energy == ElectricalPower(25)
        assert propagation.connections[
            topology.get_connection(wind.get_id(), bus.get_id()).id
        ].energy == ElectricalPower(0)

        # The consequence is a model reported infeasible even though 25 MW is within the combined
        # 30 MW the grid and wind can supply. Allocating on deliverable rather than nominal capacity
        # would give cable 20 and wind 5, and this assertion should then be inverted.
        assert set(propagation.capacity_failures) == {grid.get_id()}
        assert propagation.capacity_failures[grid.get_id()].status == EnergyFailureStatus.CAPACITY_EXCEEDED

    def test_requires_dispatch_strategy_for_junction_with_multiple_predecessors(self):
        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        bus = ElectricalBus("bus")
        load = ElectricalConsumer("load")

        units = [first_grid, second_grid, bus, load]
        topology = create_topology(
            nodes=units,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(EnergyAllocationRequiredError, match="requires a dispatch strategy"):
            EnergyNetwork(topology=topology, energy_units=units)

    def test_rejects_multiple_predecessors_for_consumer(self):
        """Two supplies feeding one load must go through a junction that says how to split the demand.

        The YAML schema already enforces this: INPUT is a single reference on a consumer and a list
        only on a junction. Without this check the domain would accept a model the schema forbids,
        and the split would be whatever the caller happened to put on each connection.
        """
        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        load = ElectricalConsumer("load")

        units = [first_grid, second_grid, load]
        topology = create_topology(
            nodes=units,
            connections=[
                (first_grid.get_id(), load.get_id()),
                (second_grid.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="only junctions support fan-in"):
            EnergyNetwork(topology=topology, energy_units=units)

    def test_rejects_multiple_predecessors_for_converter(self):
        """A converter cannot resolve fan-in either, and reaching _allocate would trip its assertion."""
        first_source = FuelGasSource("first_source")
        second_source = FuelGasSource("second_source")
        generator = GeneratorSet("generator", power_to_fuel=lambda output: output * 1_000)
        load = ElectricalConsumer("load")

        units = [first_source, second_source, generator, load]
        topology = create_topology(
            nodes=units,
            connections=[
                (first_source.get_id(), generator.get_id()),
                (second_source.get_id(), generator.get_id()),
                (generator.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="only junctions support fan-in"):
            EnergyNetwork(topology=topology, energy_units=units)

    def test_rejects_dispatch_strategy_candidate_ids_that_do_not_match_predecessors(self):
        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        missing_grid = ElectricalSource("missing_grid")
        bus = ElectricalBus(
            "bus", dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), missing_grid.get_id()))
        )
        load = ElectricalConsumer("load")

        units = [first_grid, second_grid, bus, load]
        topology = create_topology(
            nodes=units,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="must match its predecessors"):
            EnergyNetwork(topology=topology, energy_units=units)

    def test_rejects_dispatch_strategy_candidate_ids_for_junction_with_a_single_predecessor(self):
        """A single candidate leaves a strategy nothing to decide, but it must still name that candidate.

        The strategy checks used to sit behind the fan-in test, so a junction with one predecessor had its
        strategy ignored entirely and could name a node it was not connected to without any error.
        """
        grid = ElectricalSource("grid")
        other_grid = ElectricalSource("other_grid")
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(other_grid.get_id(),)))
        load = ElectricalConsumer("load")
        other_load = ElectricalConsumer("other_load")

        units = [grid, other_grid, bus, load, other_load]
        topology = create_topology(
            nodes=units,
            connections=[
                (grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
                (other_grid.get_id(), other_load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="must match its predecessors"):
            EnergyNetwork(topology=topology, energy_units=units)

    def test_accepts_dispatch_strategy_naming_the_only_predecessor(self):
        """A degenerate strategy is legal and behaves exactly like an undispatched single supply."""
        grid = ElectricalSource("grid")
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(grid.get_id(),)))
        first_load = ElectricalConsumer("first_load")
        second_load = ElectricalConsumer("second_load")

        units = [grid, bus, first_load, second_load]
        topology = create_topology(
            nodes=units,
            connections=[
                (grid.get_id(), bus.get_id()),
                (bus.get_id(), first_load.get_id()),
                (bus.get_id(), second_load.get_id()),
            ],
        )
        network = EnergyNetwork(topology=topology, energy_units=units)

        propagation = network.propagate_energy(
            {
                topology.get_connection(bus.get_id(), first_load.get_id()).id: ElectricalPower(3),
                topology.get_connection(bus.get_id(), second_load.get_id()).id: ElectricalPower(7),
            }
        )

        assert propagation.connections[
            topology.get_connection(grid.get_id(), bus.get_id()).id
        ].energy == ElectricalPower(10)
        assert not propagation.capacity_failures

        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        bus = ElectricalBus(
            "bus", dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), second_grid.get_id()))
        )
        bus_load = ElectricalConsumer("bus_load")
        direct_load = ElectricalConsumer("direct_load")

        units = [first_grid, second_grid, bus, bus_load, direct_load]
        topology = create_topology(
            nodes=units,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (first_grid.get_id(), direct_load.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), bus_load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="must have exactly one successor"):
            EnergyNetwork(topology=topology, energy_units=units)
