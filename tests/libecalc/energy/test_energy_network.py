from typing import cast

import pytest

from libecalc.energy import ElectricalPower, FuelGasRate, MechanicalPower
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
        connection_energy = network.propagate_energy(
            {
                topology.get_connection(motor.get_id(), pump.get_id()).id: MechanicalPower(4),
                topology.get_connection(bus.get_id(), base_load.get_id()).id: ElectricalPower(5),
            }
        )

        assert connection_energy == {
            topology.get_connection(source.get_id(), generator.get_id()).id: FuelGasRate(10_000),
            topology.get_connection(generator.get_id(), bus.get_id()).id: ElectricalPower(10),
            topology.get_connection(bus.get_id(), motor.get_id()).id: ElectricalPower(5),
            topology.get_connection(motor.get_id(), pump.get_id()).id: MechanicalPower(4),
            topology.get_connection(bus.get_id(), base_load.get_id()).id: ElectricalPower(5),
        }

    def test_returns_no_connection_energy_for_source_without_successors(self):
        source = FuelGasSource("source")
        topology = create_topology(nodes=[source], connections=[])
        evaluation = EnergyNetwork(
            topology=topology,
            energy_units=[source],
        )

        assert evaluation.propagate_energy({}) == {}

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

        assert network.propagate_energy(
            {topology.get_connection(cable.get_id(), consumer.get_id()).id: ElectricalPower(10)}
        ) == {
            topology.get_connection(source.get_id(), cable.get_id()).id: ElectricalPower(10 / 0.96),
            topology.get_connection(cable.get_id(), consumer.get_id()).id: ElectricalPower(10),
        }


class TestEnergyNetworkFeasibility:
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
        connection_energy = network.propagate_energy({connection.id: ElectricalPower(6)})
        capacities = {grid.get_id(): ElectricalPower(5)}

        assert connection_energy[connection.id] == ElectricalPower(6)
        assert network.is_capacity_exceeded(
            node_id=grid.get_id(),
            connection_energy=connection_energy,
            capacities=capacities,
        )

        assert not network.is_feasible(
            connection_energy=connection_energy,
            capacities=capacities,
        )

    def test_capacity_equal_to_connection_energy_is_feasible(self):
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
        connection_energy = network.propagate_energy({connection.id: ElectricalPower(5)})
        capacities = {grid.get_id(): ElectricalPower(5)}

        assert not network.is_capacity_exceeded(
            node_id=grid.get_id(),
            connection_energy=connection_energy,
            capacities=capacities,
        )
        assert network.is_feasible(
            connection_energy=connection_energy,
            capacities=capacities,
        )

    def test_missing_capacity_means_unlimited(self):
        topology, source, consumer = create_electrical_topology()
        network = EnergyNetwork(
            topology=topology,
            energy_units=[source, consumer],
        )
        connection = topology.get_connection(source.get_id(), consumer.get_id())
        connection_energy = network.propagate_energy({connection.id: ElectricalPower(5)})
        capacities = {}

        assert not network.is_capacity_exceeded(
            node_id=source.get_id(),
            connection_energy=connection_energy,
            capacities=capacities,
        )
        assert network.is_feasible(
            connection_energy=connection_energy,
            capacities=capacities,
        )

    def test_rejects_capacity_for_consumer(self):
        topology, source, consumer = create_electrical_topology()
        network = EnergyNetwork(
            topology=topology,
            energy_units=[source, consumer],
        )
        connection = topology.get_connection(source.get_id(), consumer.get_id())
        connection_energy = network.propagate_energy({connection.id: ElectricalPower(5)})

        with pytest.raises(
            InvalidEnergyNetworkInputError,
            match="Capacity provided for invalid node",
        ):
            network.is_feasible(
                connection_energy=connection_energy,
                capacities={consumer.get_id(): ElectricalPower(10)},
            )

    def test_rejects_wrong_capacity_energy_type(self):
        topology, source, consumer = create_electrical_topology()
        network = EnergyNetwork(
            topology=topology,
            energy_units=[source, consumer],
        )
        connection = topology.get_connection(source.get_id(), consumer.get_id())
        connection_energy = network.propagate_energy({connection.id: ElectricalPower(5)})

        with pytest.raises(
            InvalidEnergyNetworkInputError,
            match="must be ElectricalPower",
        ):
            network.is_feasible(
                connection_energy=connection_energy,
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
        connection_energy = network.propagate_energy(
            {
                first_connection.id: ElectricalPower(3),
                second_connection.id: ElectricalPower(4),
            }
        )
        capacities = {grid.get_id(): ElectricalPower(6)}

        assert network.is_capacity_exceeded(
            node_id=grid.get_id(),
            connection_energy=connection_energy,
            capacities=capacities,
        )

    def test_validates_all_capacities_before_checking_feasibility(self):
        topology, source, consumer = create_electrical_topology()
        network = EnergyNetwork(
            topology=topology,
            energy_units=[source, consumer],
        )
        connection = topology.get_connection(source.get_id(), consumer.get_id())
        connection_energy = network.propagate_energy({connection.id: ElectricalPower(5)})

        with pytest.raises(
            InvalidEnergyNetworkInputError,
            match="Capacity provided for invalid node",
        ):
            network.is_feasible(
                connection_energy=connection_energy,
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

        energy = network.propagate_energy(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(8)},
            capacities={grid.get_id(): ElectricalPower(5), genset.get_id(): ElectricalPower(10)},
        )

        assert energy[topology.get_connection(grid.get_id(), bus.get_id()).id] == ElectricalPower(5)
        assert energy[topology.get_connection(genset.get_id(), bus.get_id()).id] == ElectricalPower(3)
        assert energy[topology.get_connection(fuel_source.get_id(), genset.get_id()).id] == FuelGasRate(3_000)

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

        energy = network.propagate_energy(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(12)},
            capacities={first.get_id(): ElectricalPower(10), second.get_id(): ElectricalPower(10)},
        )

        assert energy[topology.get_connection(first.get_id(), bus.get_id()).id] == ElectricalPower(10)
        assert energy[topology.get_connection(second.get_id(), bus.get_id()).id] == ElectricalPower(2)
        assert energy[topology.get_connection(fuel_source.get_id(), first.get_id()).id] == FuelGasRate(10_000)
        assert energy[topology.get_connection(fuel_source.get_id(), second.get_id()).id] == FuelGasRate(14_000)

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
        energy = network.propagate_energy(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(12)},
            capacities=capacities,
        )

        assert energy[topology.get_connection(first_grid.get_id(), bus.get_id()).id] == ElectricalPower(5)
        assert energy[topology.get_connection(second_grid.get_id(), bus.get_id()).id] == ElectricalPower(7)

        # The overflow is reported rather than raised: the second grid is over its rating.
        assert network.is_capacity_exceeded(
            node_id=second_grid.get_id(), connection_energy=energy, capacities=capacities
        )
        assert not network.is_feasible(connection_energy=energy, capacities=capacities)

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
        energy = network.propagate_energy(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(25)},
            capacities=capacities,
        )

        # The cable is filled to its own 30 MW rating, so the 20 MW grid behind it is over-drawn
        # and the 10 MW wind source is left idle.
        assert energy[topology.get_connection(cable.get_id(), bus.get_id()).id] == ElectricalPower(25)
        assert energy[topology.get_connection(grid.get_id(), cable.get_id()).id] == ElectricalPower(25)
        assert energy[topology.get_connection(wind.get_id(), bus.get_id()).id] == ElectricalPower(0)

        # The consequence is a model reported infeasible even though 25 MW is within the combined
        # 30 MW the grid and wind can supply. Allocating on deliverable rather than nominal capacity
        # would give cable 20 and wind 5, and this assertion should then be inverted.
        assert network.is_capacity_exceeded(node_id=grid.get_id(), connection_energy=energy, capacities=capacities)
        assert not network.is_feasible(connection_energy=energy, capacities=capacities)

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

        energy = network.propagate_energy(
            {
                topology.get_connection(bus.get_id(), first_load.get_id()).id: ElectricalPower(3),
                topology.get_connection(bus.get_id(), second_load.get_id()).id: ElectricalPower(7),
            }
        )

        assert energy[topology.get_connection(grid.get_id(), bus.get_id()).id] == ElectricalPower(10)

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
