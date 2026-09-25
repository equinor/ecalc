import pytest

from libecalc.energy import (
    CapacityFailure,
    ElectricalPower,
    Energy,
    EnergyFailureStatus,
    FuelGasRate,
    MechanicalPower,
)
from libecalc.energy.dispatch import PriorityDispatch
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


def create_topology(nodes, connections):
    return EnergyNetworkTopology.create(
        node_input_types={node.get_id(): node.get_input_energy_type() for node in nodes},
        node_output_types={node.get_id(): node.get_output_energy_type() for node in nodes},
        connections=[(source.get_id(), target.get_id()) for source, target in connections],
    )


def connection_id(topology, source, target) -> EnergyConnectionId:
    return topology.get_connection(source.get_id(), target.get_id()).id


def energy_on(energy_network, topology, source, target) -> Energy:
    return energy_network.get_energy()[connection_id(topology, source, target)]


class TestEnergyNetworkEnergyCalculation:
    def test_calculates_input_and_output_energy_through_network(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        source = energy_unit_factory_factory(FuelGasSource, "source")
        generator = energy_unit_factory_factory(GeneratorSet, "generator", power_to_fuel=lambda output: output * 1_000)
        motor = energy_unit_factory_factory(ElectricalMotor, "motor", efficiency=0.8)
        pump = energy_unit_factory_factory(MechanicalConsumer, "pump")
        base_load = energy_unit_factory_factory(ElectricalConsumer, "base_load")

        topology = create_topology(
            nodes=[source, generator, motor, pump, base_load],
            connections=[(source, generator), (generator, motor), (motor, pump), (generator, base_load)],
        )
        energy_network_simulation = energy_network_simulation_factory(
            energy_unit_factories=[source, generator, motor], topology=topology
        )
        energy_network = energy_network_simulation.run(
            {
                connection_id(topology, motor, pump): MechanicalPower(4),
                connection_id(topology, generator, base_load): ElectricalPower(5),
            }
        )

        assert energy_network.get_energy() == {
            connection_id(topology, source, generator): FuelGasRate(10_000),
            connection_id(topology, generator, motor): ElectricalPower(5),
            connection_id(topology, motor, pump): MechanicalPower(4),
            connection_id(topology, generator, base_load): ElectricalPower(5),
        }
        assert not energy_network.get_capacity_failures()

    def test_returns_no_connection_energy_for_source_without_successors(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        source = energy_unit_factory_factory(FuelGasSource, "source")
        topology = create_topology(nodes=[source], connections=[])
        energy_network_simulation = energy_network_simulation_factory(energy_unit_factories=[source], topology=topology)

        energy_network = energy_network_simulation.run({})

        assert not energy_network.get_energy()
        assert not energy_network.get_capacity_failures()

    def test_calculates_input_energy_for_transporter(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        source = energy_unit_factory_factory(ElectricalSource, "source")
        cable = energy_unit_factory_factory(ElectricalCable, "cable", loss_fraction=0.04)
        consumer = energy_unit_factory_factory(ElectricalConsumer, "consumer")

        topology = create_topology(nodes=[source, cable, consumer], connections=[(source, cable), (cable, consumer)])
        energy_network_simulation = energy_network_simulation_factory(
            energy_unit_factories=[source, cable], topology=topology
        )

        energy_network = energy_network_simulation.run({connection_id(topology, cable, consumer): ElectricalPower(10)})

        assert energy_network.get_energy() == {
            connection_id(topology, source, cable): ElectricalPower(10 / 0.96),
            connection_id(topology, cable, consumer): ElectricalPower(10),
        }
        assert not energy_network.get_capacity_failures()


class TestEnergyNetworkCapacity:
    def test_reports_capacity_exceeded_without_capping_connection_energy(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        grid = energy_unit_factory_factory(ElectricalSource, "grid", capacity=ElectricalPower(5))
        load = energy_unit_factory_factory(ElectricalConsumer, "load")
        topology = create_topology(nodes=[grid, load], connections=[(grid, load)])
        energy_network_simulation = energy_network_simulation_factory(energy_unit_factories=[grid], topology=topology)

        energy_network = energy_network_simulation.run({connection_id(topology, grid, load): ElectricalPower(6)})

        assert energy_on(energy_network, topology, grid, load) == ElectricalPower(6)
        assert set(energy_network.get_capacity_failures()) == {grid.get_id()}
        failure = energy_network.get_capacity_failures()[grid.get_id()]
        assert isinstance(failure, CapacityFailure)
        assert failure.status == EnergyFailureStatus.CAPACITY_EXCEEDED
        assert failure.required_energy == ElectricalPower(6)
        assert failure.capacity == ElectricalPower(5)

    def test_capacity_equal_to_connection_energy_has_no_failure(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        grid = energy_unit_factory_factory(ElectricalSource, "grid", capacity=ElectricalPower(5))
        load = energy_unit_factory_factory(ElectricalConsumer, "load")
        topology = create_topology(nodes=[grid, load], connections=[(grid, load)])
        energy_network_simulation = energy_network_simulation_factory(energy_unit_factories=[grid], topology=topology)

        energy_network = energy_network_simulation.run({connection_id(topology, grid, load): ElectricalPower(5)})

        assert not energy_network.get_capacity_failures()

    def test_missing_capacity_means_unlimited(self, energy_network_simulation_factory, energy_unit_factory_factory):
        grid = energy_unit_factory_factory(ElectricalSource, "grid")
        load = energy_unit_factory_factory(ElectricalConsumer, "load")
        topology = create_topology(nodes=[grid, load], connections=[(grid, load)])
        energy_network_simulation = energy_network_simulation_factory(energy_unit_factories=[grid], topology=topology)

        energy_network = energy_network_simulation.run({connection_id(topology, grid, load): ElectricalPower(5)})

        assert not energy_network.get_capacity_failures()

    def test_zero_capacity_is_a_limit_not_unlimited(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        grid = energy_unit_factory_factory(ElectricalSource, "grid", capacity=ElectricalPower(0))
        load = energy_unit_factory_factory(ElectricalConsumer, "load")
        topology = create_topology(nodes=[grid, load], connections=[(grid, load)])
        energy_network_simulation = energy_network_simulation_factory(energy_unit_factories=[grid], topology=topology)

        energy_network = energy_network_simulation.run({connection_id(topology, grid, load): ElectricalPower(1)})

        assert set(energy_network.get_capacity_failures()) == {grid.get_id()}

    def test_compares_capacity_with_total_outgoing_energy(
        self, energy_network_simulation_factory, energy_unit_factory_factory
    ):
        grid = energy_unit_factory_factory(ElectricalSource, "grid", capacity=ElectricalPower(6))
        first_load = energy_unit_factory_factory(ElectricalConsumer, "first_load")
        second_load = energy_unit_factory_factory(ElectricalConsumer, "second_load")
        topology = create_topology(
            nodes=[grid, first_load, second_load], connections=[(grid, first_load), (grid, second_load)]
        )
        energy_network_simulation = energy_network_simulation_factory(energy_unit_factories=[grid], topology=topology)

        energy_network = energy_network_simulation.run(
            {
                connection_id(topology, grid, first_load): ElectricalPower(3),
                connection_id(topology, grid, second_load): ElectricalPower(4),
            }
        )

        # Every consumer keeps its full demand; the aggregate draw is reported against the source.
        assert energy_on(energy_network, topology, grid, first_load) == ElectricalPower(3)
        assert energy_on(energy_network, topology, grid, second_load) == ElectricalPower(4)
        assert energy_network.get_capacity_failures()[grid.get_id()].status == EnergyFailureStatus.CAPACITY_EXCEEDED
        assert energy_network.get_capacity_failures()[grid.get_id()].required_energy == ElectricalPower(7)


class TestJunctionDispatch:
    def test_dispatches_to_shore_before_genset(
        self, energy_network_simulation_factory, energy_unit_factory_factory, junction_factory_factory
    ):
        """Power from shore is filled first, and the generator set covers only the shortfall."""
        fuel_source = energy_unit_factory_factory(FuelGasSource, "fuel_source")
        grid = energy_unit_factory_factory(ElectricalSource, "grid", capacity=ElectricalPower(5))
        genset = energy_unit_factory_factory(
            GeneratorSet, "genset", power_to_fuel=lambda power: power * 1_000, capacity=ElectricalPower(10)
        )
        bus = junction_factory_factory(
            ElectricalBus,
            "bus",
            dispatch_strategy=PriorityDispatch(order=(grid.get_id(), genset.get_id())),
            input_capacities={grid.get_id(): ElectricalPower(5), genset.get_id(): ElectricalPower(10)},
        )
        load = energy_unit_factory_factory(ElectricalConsumer, "load")

        topology = create_topology(
            nodes=[fuel_source, grid, genset, bus, load],
            connections=[(fuel_source, genset), (grid, bus), (genset, bus), (bus, load)],
        )
        energy_network_simulation = energy_network_simulation_factory(
            energy_unit_factories=[fuel_source, grid, genset, bus], topology=topology
        )

        energy_network = energy_network_simulation.run({connection_id(topology, bus, load): ElectricalPower(8)})

        assert energy_on(energy_network, topology, grid, bus) == ElectricalPower(5)
        assert energy_on(energy_network, topology, genset, bus) == ElectricalPower(3)
        assert energy_on(energy_network, topology, fuel_source, genset) == FuelGasRate(3_000)
        assert not energy_network.get_capacity_failures()

    def test_separate_genset_curves_reproduce_legacy_fuel_jump(
        self, energy_network_simulation_factory, energy_unit_factory_factory, junction_factory_factory
    ):
        """Per-generator curves replace the jumps encoded in a single legacy curve."""
        fuel_source = energy_unit_factory_factory(FuelGasSource, "fuel_source")
        first = energy_unit_factory_factory(GeneratorSet, "first_genset", power_to_fuel=lambda power: power * 1_000)
        second = energy_unit_factory_factory(
            GeneratorSet, "second_genset", power_to_fuel=lambda power: 10_000 + power * 2_000
        )
        bus = junction_factory_factory(
            ElectricalBus,
            "bus",
            dispatch_strategy=PriorityDispatch(order=(first.get_id(), second.get_id())),
            input_capacities={first.get_id(): ElectricalPower(10), second.get_id(): ElectricalPower(10)},
        )
        load = energy_unit_factory_factory(ElectricalConsumer, "load")

        topology = create_topology(
            nodes=[fuel_source, first, second, bus, load],
            connections=[(fuel_source, first), (fuel_source, second), (first, bus), (second, bus), (bus, load)],
        )
        energy_network_simulation = energy_network_simulation_factory(
            energy_unit_factories=[fuel_source, first, second, bus], topology=topology
        )

        energy_network = energy_network_simulation.run({connection_id(topology, bus, load): ElectricalPower(12)})

        assert energy_on(energy_network, topology, first, bus) == ElectricalPower(10)
        assert energy_on(energy_network, topology, second, bus) == ElectricalPower(2)
        assert energy_on(energy_network, topology, fuel_source, first) == FuelGasRate(10_000)
        assert energy_on(energy_network, topology, fuel_source, second) == FuelGasRate(14_000)
        assert not energy_network.get_capacity_failures()

    @pytest.mark.parametrize(
        ("second_grid_capacity", "expected_failures"),
        [
            pytest.param(ElectricalPower(10), {}, id="ratings above the dispatch limits"),
            pytest.param(
                ElectricalPower(5),
                {"second_grid": (ElectricalPower(7), ElectricalPower(5))},
                id="last candidate rated at its dispatch limit",
            ),
            pytest.param(None, {}, id="last candidate without a rating"),
        ],
    )
    def test_overflow_above_dispatch_limits_is_judged_only_by_supplier_ratings(
        self,
        energy_network_simulation_factory,
        energy_unit_factory_factory,
        junction_factory_factory,
        second_grid_capacity,
        expected_failures,
    ):
        first_grid = energy_unit_factory_factory(ElectricalSource, "first_grid", capacity=ElectricalPower(10))
        second_grid = energy_unit_factory_factory(ElectricalSource, "second_grid", capacity=second_grid_capacity)
        bus = junction_factory_factory(
            ElectricalBus,
            "bus",
            dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), second_grid.get_id())),
            input_capacities={first_grid.get_id(): ElectricalPower(5), second_grid.get_id(): ElectricalPower(5)},
        )
        load = energy_unit_factory_factory(ElectricalConsumer, "load")

        topology = create_topology(
            nodes=[first_grid, second_grid, bus, load],
            connections=[(first_grid, bus), (second_grid, bus), (bus, load)],
        )
        energy_network_simulation = energy_network_simulation_factory(
            energy_unit_factories=[first_grid, second_grid, bus], topology=topology
        )

        energy_network = energy_network_simulation.run({connection_id(topology, bus, load): ElectricalPower(12)})

        assert energy_on(energy_network, topology, first_grid, bus) == ElectricalPower(5)
        assert energy_on(energy_network, topology, second_grid, bus) == ElectricalPower(7)
        names_by_id = {first_grid.get_id(): "first_grid", second_grid.get_id(): "second_grid"}
        assert {
            names_by_id[unit_id]: (failure.required_energy, failure.capacity)
            for unit_id, failure in energy_network.get_capacity_failures().items()
        } == expected_failures

    def test_omitted_input_limit_does_not_inherit_the_supplier_rating(
        self, energy_network_simulation_factory, energy_unit_factory_factory, junction_factory_factory
    ):
        grid = energy_unit_factory_factory(ElectricalSource, "grid", capacity=ElectricalPower(5))
        wind = energy_unit_factory_factory(ElectricalSource, "wind")
        bus = junction_factory_factory(
            ElectricalBus, "bus", dispatch_strategy=PriorityDispatch(order=(grid.get_id(), wind.get_id()))
        )
        load = energy_unit_factory_factory(ElectricalConsumer, "load")
        topology = create_topology(nodes=[grid, wind, bus, load], connections=[(grid, bus), (wind, bus), (bus, load)])
        energy_network_simulation = energy_network_simulation_factory(
            energy_unit_factories=[grid, wind, bus], topology=topology
        )

        energy_network = energy_network_simulation.run({connection_id(topology, bus, load): ElectricalPower(8)})

        # The grid's own 5 MW rating is not used as its dispatch limit, so it takes all 8 and is over its rating.
        assert energy_on(energy_network, topology, grid, bus) == ElectricalPower(8)
        assert energy_on(energy_network, topology, wind, bus) == ElectricalPower(0)
        assert set(energy_network.get_capacity_failures()) == {grid.get_id()}

    def _shore_and_wind(
        self, energy_unit_factory_factory, junction_factory_factory, cable_limit_at_bus: ElectricalPower
    ):
        shore = energy_unit_factory_factory(ElectricalSource, "shore", capacity=ElectricalPower(20))
        cable = energy_unit_factory_factory(ElectricalCable, "cable", loss_fraction=0.03)
        wind = energy_unit_factory_factory(ElectricalSource, "wind", capacity=ElectricalPower(4.4))
        bus = junction_factory_factory(
            ElectricalBus,
            "bus",
            dispatch_strategy=PriorityDispatch(order=(cable.get_id(), wind.get_id())),
            input_capacities={cable.get_id(): cable_limit_at_bus, wind.get_id(): ElectricalPower(4.4)},
        )
        load = energy_unit_factory_factory(ElectricalConsumer, "load")
        topology = create_topology(
            nodes=[shore, cable, wind, bus, load],
            connections=[(shore, cable), (cable, bus), (wind, bus), (bus, load)],
        )
        return topology, shore, cable, wind, bus, load

    def test_input_limit_measured_after_upstream_loss_keeps_shore_within_rating(
        self, energy_network_simulation_factory, energy_unit_factory_factory, junction_factory_factory
    ):
        """20 MW from shore through a 97 % cable is 19.4 MW at the bus, the limit a modeller would declare."""
        topology, shore, cable, wind, bus, load = self._shore_and_wind(
            energy_unit_factory_factory, junction_factory_factory, cable_limit_at_bus=ElectricalPower(19.4)
        )
        energy_network_simulation = energy_network_simulation_factory(
            energy_unit_factories=[shore, cable, wind, bus], topology=topology
        )

        energy_network = energy_network_simulation.run({connection_id(topology, bus, load): ElectricalPower(22)})

        assert energy_on(energy_network, topology, cable, bus) == ElectricalPower(19.4)
        assert energy_on(energy_network, topology, wind, bus).value == pytest.approx(2.6)
        assert energy_on(energy_network, topology, shore, cable).value == pytest.approx(20)
        assert not energy_network.get_capacity_failures()

    def test_overstated_input_limit_overloads_upstream_without_redispatch(
        self, energy_network_simulation_factory, energy_unit_factory_factory, junction_factory_factory
    ):
        topology, shore, cable, wind, bus, load = self._shore_and_wind(
            energy_unit_factory_factory, junction_factory_factory, cable_limit_at_bus=ElectricalPower(25)
        )
        energy_network_simulation = energy_network_simulation_factory(
            energy_unit_factories=[shore, cable, wind, bus], topology=topology
        )

        energy_network = energy_network_simulation.run({connection_id(topology, bus, load): ElectricalPower(22)})

        # The bus trusts its declared limit: wind stays idle and shore is overdrawn rather than relieved.
        assert energy_on(energy_network, topology, cable, bus) == ElectricalPower(22)
        assert energy_on(energy_network, topology, wind, bus) == ElectricalPower(0)
        assert energy_on(energy_network, topology, shore, cable).value == pytest.approx(22 / 0.97)
        assert set(energy_network.get_capacity_failures()) == {shore.get_id()}

    def test_nested_junction_dispatches_the_share_it_receives(
        self, energy_network_simulation_factory, energy_unit_factory_factory, junction_factory_factory
    ):
        first_grid = energy_unit_factory_factory(ElectricalSource, "first_grid")
        second_grid = energy_unit_factory_factory(ElectricalSource, "second_grid")
        backup = energy_unit_factory_factory(ElectricalSource, "backup")
        inner_bus = junction_factory_factory(
            ElectricalBus,
            "inner_bus",
            dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), second_grid.get_id())),
            input_capacities={first_grid.get_id(): ElectricalPower(4)},
        )
        outer_bus = junction_factory_factory(
            ElectricalBus,
            "outer_bus",
            dispatch_strategy=PriorityDispatch(order=(inner_bus.get_id(), backup.get_id())),
            input_capacities={inner_bus.get_id(): ElectricalPower(14)},
        )
        load = energy_unit_factory_factory(ElectricalConsumer, "load")
        topology = create_topology(
            nodes=[first_grid, second_grid, backup, inner_bus, outer_bus, load],
            connections=[
                (first_grid, inner_bus),
                (second_grid, inner_bus),
                (inner_bus, outer_bus),
                (backup, outer_bus),
                (outer_bus, load),
            ],
        )
        energy_network_simulation = energy_network_simulation_factory(
            energy_unit_factories=[first_grid, second_grid, backup, inner_bus, outer_bus], topology=topology
        )

        energy_network = energy_network_simulation.run({connection_id(topology, outer_bus, load): ElectricalPower(16)})

        assert energy_on(energy_network, topology, inner_bus, outer_bus) == ElectricalPower(14)
        assert energy_on(energy_network, topology, backup, outer_bus) == ElectricalPower(2)
        assert energy_on(energy_network, topology, first_grid, inner_bus) == ElectricalPower(4)
        assert energy_on(energy_network, topology, second_grid, inner_bus) == ElectricalPower(10)

    def test_input_that_also_supplies_another_node_reports_its_total_overload(
        self, energy_network_simulation_factory, energy_unit_factory_factory, junction_factory_factory
    ):
        wind = energy_unit_factory_factory(ElectricalSource, "wind", capacity=ElectricalPower(5))
        grid = energy_unit_factory_factory(ElectricalSource, "grid", capacity=ElectricalPower(10))
        bus = junction_factory_factory(
            ElectricalBus,
            "bus",
            dispatch_strategy=PriorityDispatch(order=(wind.get_id(), grid.get_id())),
            input_capacities={wind.get_id(): ElectricalPower(5)},
        )
        bus_load = energy_unit_factory_factory(ElectricalConsumer, "bus_load")
        direct_load = energy_unit_factory_factory(ElectricalConsumer, "direct_load")
        topology = create_topology(
            nodes=[wind, grid, bus, bus_load, direct_load],
            connections=[(wind, bus), (wind, direct_load), (grid, bus), (bus, bus_load)],
        )
        energy_network_simulation = energy_network_simulation_factory(
            energy_unit_factories=[wind, grid, bus], topology=topology
        )

        energy_network = energy_network_simulation.run(
            {
                connection_id(topology, bus, bus_load): ElectricalPower(6),
                connection_id(topology, wind, direct_load): ElectricalPower(3),
            }
        )

        # The bus limit ignores the direct load, so wind is asked for 8 against its rating of 5.
        assert energy_on(energy_network, topology, wind, bus) == ElectricalPower(5)
        assert energy_on(energy_network, topology, wind, direct_load) == ElectricalPower(3)
        assert energy_on(energy_network, topology, grid, bus) == ElectricalPower(1)
        assert set(energy_network.get_capacity_failures()) == {wind.get_id()}
