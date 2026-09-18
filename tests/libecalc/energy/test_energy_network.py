import pytest

from libecalc.energy import CapacityFailure, ElectricalPower, EnergyFailureStatus, FuelGasRate, MechanicalPower
from libecalc.energy.dispatch import PriorityDispatch
from libecalc.energy.energy_network_topology import EnergyNetworkTopology
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
)


def create_topology(nodes, connections):
    return EnergyNetworkTopology.create(
        node_input_types={node.get_id(): node.get_input_energy_type() for node in nodes},
        node_output_types={node.get_id(): node.get_output_energy_type() for node in nodes},
        connections=connections,
    )


def create_electrical_topology(energy_unit_factory_factory):
    source = energy_unit_factory_factory(ElectricalSource, "source")
    consumer = ElectricalConsumer("consumer", output_energy=ElectricalPower(0))
    topology = create_topology(
        nodes=[source, consumer],
        connections=[
            (source.get_id(), consumer.get_id()),
        ],
    )
    return topology, source, consumer


class TestEnergyNetworkEnergyCalculation:
    def test_calculates_input_and_output_energy_through_network(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        source = energy_unit_factory_factory(FuelGasSource, "source")
        generator = energy_unit_factory_factory(GeneratorSet, "generator", power_to_fuel=lambda output: output * 1_000)
        bus = ElectricalBus("bus")
        motor = energy_unit_factory_factory(ElectricalMotor, "motor", efficiency=0.8)
        pump = MechanicalConsumer("pump", output_energy=MechanicalPower(0))
        base_load = ElectricalConsumer("base_load", output_energy=ElectricalPower(0))

        nodes = [source, generator, bus, motor, pump, base_load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (source.get_id(), generator.get_id()),
                (generator.get_id(), bus.get_id()),
                (bus.get_id(), motor.get_id()),
                (motor.get_id(), pump.get_id()),
                (bus.get_id(), base_load.get_id()),
            ],
        )
        energy_network_simulation = energy_network_simulation_factory(
            junctions=[bus], energy_unit_factories=[source, generator, motor], topology=topology
        )
        energy_network = energy_network_simulation.run(
            {
                topology.get_connection(motor.get_id(), pump.get_id()).id: MechanicalPower(4),
                topology.get_connection(bus.get_id(), base_load.get_id()).id: ElectricalPower(5),
            }
        )

        assert energy_network.get_energy() == {
            topology.get_connection(source.get_id(), generator.get_id()).id: FuelGasRate(10_000),
            topology.get_connection(generator.get_id(), bus.get_id()).id: ElectricalPower(10),
            topology.get_connection(bus.get_id(), motor.get_id()).id: ElectricalPower(5),
            topology.get_connection(motor.get_id(), pump.get_id()).id: MechanicalPower(4),
            topology.get_connection(bus.get_id(), base_load.get_id()).id: ElectricalPower(5),
        }
        assert not energy_network.get_capacity_failures()

    def test_returns_no_connection_energy_for_source_without_successors(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        source = energy_unit_factory_factory(FuelGasSource, "source")
        topology = create_topology(nodes=[source], connections=[])
        energy_network_simulation = energy_network_simulation_factory(
            junctions=[], energy_unit_factories=[source], topology=topology
        )

        energy_network = energy_network_simulation.run({})

        assert not energy_network.get_energy()
        assert not energy_network.get_capacity_failures()

    def test_calculates_input_energy_for_transporter(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        source = energy_unit_factory_factory(ElectricalSource, "source")
        cable = energy_unit_factory_factory(ElectricalCable, "cable", loss_fraction=0.04)
        consumer = ElectricalConsumer("consumer", output_energy=ElectricalPower(0))

        nodes = [source, cable, consumer]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (source.get_id(), cable.get_id()),
                (cable.get_id(), consumer.get_id()),
            ],
        )

        energy_network_simulation = energy_network_simulation_factory(
            junctions=[], energy_unit_factories=[source, cable], topology=topology
        )

        energy_network = energy_network_simulation.run(
            {topology.get_connection(cable.get_id(), consumer.get_id()).id: ElectricalPower(10)}
        )

        assert energy_network.get_energy() == {
            topology.get_connection(source.get_id(), cable.get_id()).id: ElectricalPower(10 / 0.96),
            topology.get_connection(cable.get_id(), consumer.get_id()).id: ElectricalPower(10),
        }
        assert not energy_network.get_capacity_failures()


class TestEnergyNetworkCapacity:
    def test_reports_capacity_exceeded_without_capping_connection_energy(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        grid = energy_unit_factory_factory(ElectricalSource, "grid")
        load = ElectricalConsumer("load", output_energy=ElectricalPower(0))
        topology = create_topology(
            nodes=[grid, load],
            connections=[(grid.get_id(), load.get_id())],
        )
        energy_network_simulation = energy_network_simulation_factory(
            junctions=[], energy_unit_factories=[grid], topology=topology
        )
        connection = topology.get_connection(grid.get_id(), load.get_id())
        capacities = {grid.get_id(): ElectricalPower(5)}
        energy_network = energy_network_simulation.run(
            {connection.id: ElectricalPower(6)},
            capacities=capacities,
        )

        assert energy_network.get_energy()[connection.id] == ElectricalPower(6)
        assert set(energy_network.get_capacity_failures()) == {grid.get_id()}
        assert isinstance(energy_network.get_capacity_failures()[grid.get_id()], CapacityFailure)
        assert energy_network.get_capacity_failures()[grid.get_id()].status == EnergyFailureStatus.CAPACITY_EXCEEDED
        assert energy_network.get_capacity_failures()[grid.get_id()].required_energy == ElectricalPower(6)
        assert energy_network.get_capacity_failures()[grid.get_id()].capacity == ElectricalPower(5)

    def test_capacity_equal_to_connection_energy_has_no_failure(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        grid = energy_unit_factory_factory(ElectricalSource, "grid")
        load = ElectricalConsumer("load", output_energy=ElectricalPower(0))
        topology = create_topology(
            nodes=[grid, load],
            connections=[(grid.get_id(), load.get_id())],
        )
        energy_network_simulation = energy_network_simulation_factory(
            junctions=[], energy_unit_factories=[grid], topology=topology
        )
        connection = topology.get_connection(grid.get_id(), load.get_id())
        capacities = {grid.get_id(): ElectricalPower(5)}
        energy_network = energy_network_simulation.run(
            {connection.id: ElectricalPower(5)},
            capacities=capacities,
        )

        assert not energy_network.get_capacity_failures()

    def test_missing_capacity_means_unlimited(self, energy_network_simulation_factory, energy_unit_factory_factory):
        topology, grid, load = create_electrical_topology(energy_unit_factory_factory)
        energy_network_simulation = energy_network_simulation_factory(
            junctions=[], energy_unit_factories=[grid], topology=topology
        )
        connection = topology.get_connection(grid.get_id(), load.get_id())
        energy_network = energy_network_simulation.run({connection.id: ElectricalPower(5)})

        assert not energy_network.get_capacity_failures()

    def test_compares_capacity_with_total_outgoing_energy(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        grid = energy_unit_factory_factory(ElectricalSource, "grid")
        first_load = ElectricalConsumer("first_load", output_energy=ElectricalPower(0))
        second_load = ElectricalConsumer("second_load", output_energy=ElectricalPower(0))
        topology = create_topology(
            nodes=[grid, first_load, second_load],
            connections=[
                (grid.get_id(), first_load.get_id()),
                (grid.get_id(), second_load.get_id()),
            ],
        )
        energy_network_simulation = energy_network_simulation_factory(
            junctions=[], energy_unit_factories=[grid], topology=topology
        )
        first_connection = topology.get_connection(grid.get_id(), first_load.get_id())
        second_connection = topology.get_connection(grid.get_id(), second_load.get_id())
        capacities = {grid.get_id(): ElectricalPower(6)}
        energy_network = energy_network_simulation.run(
            {
                first_connection.id: ElectricalPower(3),
                second_connection.id: ElectricalPower(4),
            },
            capacities=capacities,
        )
        assert energy_network.get_capacity_failures()[grid.get_id()].status == EnergyFailureStatus.CAPACITY_EXCEEDED


class TestJunctionDispatch:
    def test_dispatches_to_shore_before_genset(self, energy_network_simulation_factory, energy_unit_factory_factory):
        """Power from shore is filled first, and the generator set covers only the shortfall."""
        fuel_source = energy_unit_factory_factory(FuelGasSource, "fuel_source")
        grid = energy_unit_factory_factory(ElectricalSource, "grid")
        genset = energy_unit_factory_factory(GeneratorSet, "genset", power_to_fuel=lambda power: power * 1_000)
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(grid.get_id(), genset.get_id())))
        load = ElectricalConsumer("load", output_energy=ElectricalPower(0))

        nodes = [fuel_source, grid, genset, bus, load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (fuel_source.get_id(), genset.get_id()),
                (grid.get_id(), bus.get_id()),
                (genset.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        energy_network_simulation = energy_network_simulation_factory(
            junctions=[bus], energy_unit_factories=[fuel_source, grid, genset], topology=topology
        )

        energy_network = energy_network_simulation.run(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(8)},
            capacities={grid.get_id(): ElectricalPower(5), genset.get_id(): ElectricalPower(10)},
        )

        assert energy_network.get_energy()[topology.get_connection(grid.get_id(), bus.get_id()).id] == ElectricalPower(
            5
        )
        assert energy_network.get_energy()[
            topology.get_connection(genset.get_id(), bus.get_id()).id
        ] == ElectricalPower(3)
        assert energy_network.get_energy()[
            topology.get_connection(fuel_source.get_id(), genset.get_id()).id
        ] == FuelGasRate(3_000)
        assert not energy_network.get_capacity_failures()

    def test_separate_genset_curves_reproduce_legacy_fuel_jump(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        """Per-generator curves replace the jumps encoded in a single legacy curve."""
        fuel_source = energy_unit_factory_factory(FuelGasSource, "fuel_source")
        first = energy_unit_factory_factory(GeneratorSet, "first_genset", power_to_fuel=lambda power: power * 1_000)
        second = energy_unit_factory_factory(
            GeneratorSet, "second_genset", power_to_fuel=lambda power: 10_000 + power * 2_000
        )
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(first.get_id(), second.get_id())))
        load = ElectricalConsumer("load", output_energy=ElectricalPower(0))

        nodes = [fuel_source, first, second, bus, load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (fuel_source.get_id(), first.get_id()),
                (fuel_source.get_id(), second.get_id()),
                (first.get_id(), bus.get_id()),
                (second.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        energy_network_simulation = energy_network_simulation_factory(
            junctions=[bus], energy_unit_factories=[fuel_source, first, second], topology=topology
        )

        energy_network = energy_network_simulation.run(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(12)},
            capacities={first.get_id(): ElectricalPower(10), second.get_id(): ElectricalPower(10)},
        )

        assert energy_network.get_energy()[topology.get_connection(first.get_id(), bus.get_id()).id] == ElectricalPower(
            10
        )
        assert energy_network.get_energy()[
            topology.get_connection(second.get_id(), bus.get_id()).id
        ] == ElectricalPower(2)
        assert energy_network.get_energy()[
            topology.get_connection(fuel_source.get_id(), first.get_id()).id
        ] == FuelGasRate(10_000)
        assert energy_network.get_energy()[
            topology.get_connection(fuel_source.get_id(), second.get_id()).id
        ] == FuelGasRate(14_000)
        assert not energy_network.get_capacity_failures()

    def test_overflows_last_candidate_when_total_capacity_is_insufficient(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        """Demand beyond total capacity lands on the last candidate rather than raising."""
        first_grid = energy_unit_factory_factory(ElectricalSource, "first_grid")
        second_grid = energy_unit_factory_factory(ElectricalSource, "second_grid")
        bus = ElectricalBus(
            "bus", dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), second_grid.get_id()))
        )
        load = ElectricalConsumer("load", output_energy=ElectricalPower(0))

        nodes = [first_grid, second_grid, bus, load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        energy_network_simulation = energy_network_simulation_factory(
            junctions=[bus], energy_unit_factories=[first_grid, second_grid], topology=topology
        )

        capacities = {first_grid.get_id(): ElectricalPower(5), second_grid.get_id(): ElectricalPower(5)}
        energy_network = energy_network_simulation.run(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(12)},
            capacities=capacities,
        )

        assert energy_network.get_energy()[
            topology.get_connection(first_grid.get_id(), bus.get_id()).id
        ] == ElectricalPower(5)
        assert energy_network.get_energy()[
            topology.get_connection(second_grid.get_id(), bus.get_id()).id
        ] == ElectricalPower(7)

        # The overflow is reported rather than raised: the second grid is over its rating.
        assert set(energy_network.get_capacity_failures()) == {second_grid.get_id()}
        assert (
            energy_network.get_capacity_failures()[second_grid.get_id()].status == EnergyFailureStatus.CAPACITY_EXCEEDED
        )

    def test_dispatch_uses_cable_capacity_not_upstream_grid_capacity(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        """Availability is a candidate's own capacity, not what the chain behind it can deliver."""
        grid = energy_unit_factory_factory(ElectricalSource, "grid")
        cable = energy_unit_factory_factory(ElectricalCable, "cable")
        wind = energy_unit_factory_factory(ElectricalSource, "wind")
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(cable.get_id(), wind.get_id())))
        load = ElectricalConsumer("load", output_energy=ElectricalPower(0))

        nodes = [grid, cable, wind, bus, load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (grid.get_id(), cable.get_id()),
                (cable.get_id(), bus.get_id()),
                (wind.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        energy_network_simulation = energy_network_simulation_factory(
            junctions=[bus], energy_unit_factories=[grid, cable, wind], topology=topology
        )

        capacities = {
            grid.get_id(): ElectricalPower(20),
            cable.get_id(): ElectricalPower(30),
            wind.get_id(): ElectricalPower(10),
        }
        energy_network = energy_network_simulation.run(
            {topology.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(25)},
            capacities=capacities,
        )

        # The cable is filled to its own 30 MW rating, so the 20 MW grid behind it is over-drawn
        # and the 10 MW wind source is left idle.
        assert energy_network.get_energy()[topology.get_connection(cable.get_id(), bus.get_id()).id] == ElectricalPower(
            25
        )
        assert energy_network.get_energy()[
            topology.get_connection(grid.get_id(), cable.get_id()).id
        ] == ElectricalPower(25)
        assert energy_network.get_energy()[topology.get_connection(wind.get_id(), bus.get_id()).id] == ElectricalPower(
            0
        )

        # The consequence is a model reported infeasible even though 25 MW is within the combined
        # 30 MW the grid and wind can supply. Allocating on deliverable rather than nominal capacity
        # would give cable 20 and wind 5, and this assertion should then be inverted.
        assert set(energy_network.get_capacity_failures()) == {grid.get_id()}
        assert energy_network.get_capacity_failures()[grid.get_id()].status == EnergyFailureStatus.CAPACITY_EXCEEDED

    def test_requires_dispatch_strategy_for_junction_with_multiple_predecessors(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        first_grid = energy_unit_factory_factory(ElectricalSource, "first_grid")
        second_grid = energy_unit_factory_factory(ElectricalSource, "second_grid")
        bus = ElectricalBus("bus")
        load = ElectricalConsumer("load", output_energy=ElectricalPower(0))

        nodes = [first_grid, second_grid, bus, load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(EnergyAllocationRequiredError, match="requires a dispatch strategy"):
            energy_network_simulation_factory(
                junctions=[bus], energy_unit_factories=[first_grid, second_grid], topology=topology
            )

    def test_rejects_multiple_predecessors_for_consumer(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        """Two supplies feeding one load must go through a junction that says how to split the demand.

        The YAML schema already enforces this: INPUT is a single reference on a consumer and a list
        only on a junction. Without this check the domain would accept a model the schema forbids,
        and the split would be whatever the caller happened to put on each connection.
        """
        first_grid = energy_unit_factory_factory(ElectricalSource, "first_grid")
        second_grid = energy_unit_factory_factory(ElectricalSource, "second_grid")
        load = ElectricalConsumer("load", output_energy=ElectricalPower(0))

        nodes = [first_grid, second_grid, load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (first_grid.get_id(), load.get_id()),
                (second_grid.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="only junctions support fan-in"):
            energy_network_simulation_factory(
                junctions=[], energy_unit_factories=[first_grid, second_grid], topology=topology
            )

    def test_rejects_multiple_predecessors_for_converter(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        """A converter cannot resolve fan-in either, and reaching _allocate would trip its assertion."""
        first_source = energy_unit_factory_factory(FuelGasSource, "first_source")
        second_source = energy_unit_factory_factory(FuelGasSource, "second_source")
        generator = energy_unit_factory_factory(GeneratorSet, "generator", power_to_fuel=lambda output: output * 1_000)
        load = ElectricalConsumer("load", output_energy=ElectricalPower(0))

        nodes = [first_source, second_source, generator, load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (first_source.get_id(), generator.get_id()),
                (second_source.get_id(), generator.get_id()),
                (generator.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="only junctions support fan-in"):
            energy_network_simulation_factory(
                junctions=[], energy_unit_factories=[first_source, second_source, generator], topology=topology
            )

    def test_rejects_dispatch_strategy_candidate_ids_that_do_not_match_predecessors(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        first_grid = energy_unit_factory_factory(ElectricalSource, "first_grid")
        second_grid = energy_unit_factory_factory(ElectricalSource, "second_grid")
        missing_grid = energy_unit_factory_factory(ElectricalSource, "missing_grid")
        bus = ElectricalBus(
            "bus", dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), missing_grid.get_id()))
        )
        load = ElectricalConsumer("load", output_energy=ElectricalPower(0))

        nodes = [first_grid, second_grid, bus, load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="must match its predecessors"):
            energy_network_simulation_factory(
                junctions=[bus], energy_unit_factories=[first_grid, second_grid], topology=topology
            )

    def test_rejects_dispatch_strategy_candidate_ids_for_junction_with_a_single_predecessor(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        """A single candidate leaves a strategy nothing to decide, but it must still name that candidate.

        The strategy checks used to sit behind the fan-in test, so a junction with one predecessor had its
        strategy ignored entirely and could name a node it was not connected to without any error.
        """
        grid = energy_unit_factory_factory(ElectricalSource, "grid")
        other_grid = energy_unit_factory_factory(ElectricalSource, "other_grid")
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(other_grid.get_id(),)))
        load = ElectricalConsumer("load", output_energy=ElectricalPower(0))
        other_load = ElectricalConsumer("other_load", output_energy=ElectricalPower(0))

        nodes = [grid, other_grid, bus, load, other_load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
                (other_grid.get_id(), other_load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="must match its predecessors"):
            energy_network_simulation_factory(
                junctions=[bus], energy_unit_factories=[grid, other_grid], topology=topology
            )

    def test_accepts_dispatch_strategy_naming_the_only_predecessor(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        """A degenerate strategy is legal and behaves exactly like an undispatched single supply."""
        grid = energy_unit_factory_factory(ElectricalSource, "grid")
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(grid.get_id(),)))
        first_load = ElectricalConsumer("first_load", output_energy=ElectricalPower(0))
        second_load = ElectricalConsumer("second_load", output_energy=ElectricalPower(0))

        nodes = [grid, bus, first_load, second_load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (grid.get_id(), bus.get_id()),
                (bus.get_id(), first_load.get_id()),
                (bus.get_id(), second_load.get_id()),
            ],
        )
        energy_network_simulation = energy_network_simulation_factory(
            junctions=[bus], energy_unit_factories=[grid], topology=topology
        )

        energy_network = energy_network_simulation.run(
            {
                topology.get_connection(bus.get_id(), first_load.get_id()).id: ElectricalPower(3),
                topology.get_connection(bus.get_id(), second_load.get_id()).id: ElectricalPower(7),
            }
        )

        assert energy_network.get_energy()[topology.get_connection(grid.get_id(), bus.get_id()).id] == ElectricalPower(
            10
        )
        assert not energy_network.get_capacity_failures()

        first_grid = energy_unit_factory_factory(ElectricalSource, "first_grid")
        second_grid = energy_unit_factory_factory(ElectricalSource, "second_grid")
        bus = ElectricalBus(
            "bus", dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), second_grid.get_id()))
        )
        bus_load = ElectricalConsumer("bus_load", output_energy=ElectricalPower(0))
        direct_load = ElectricalConsumer("direct_load", output_energy=ElectricalPower(0))

        nodes = [first_grid, second_grid, bus, bus_load, direct_load]
        topology = create_topology(
            nodes=nodes,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (first_grid.get_id(), direct_load.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), bus_load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="must have exactly one successor"):
            energy_network_simulation_factory(
                junctions=[bus], energy_unit_factories=[first_grid, second_grid], topology=topology
            )
