import pytest

from libecalc.energy import Consumer, ElectricalPower, FuelGasRate
from libecalc.energy.dispatch import PriorityDispatch
from libecalc.energy.energy_network_topology import EnergyConnection, EnergyConnectionId, EnergyNetworkTopology
from libecalc.energy.energy_units import (
    ElectricalBus,
    ElectricalCable,
    ElectricalSource,
    FuelGasSource,
)

# Units that draw energy need an incoming connection, which only exists once the topology does, so topology tests
# identify nodes through factories instead.
from libecalc.energy.errors import InvalidEnergyNetworkError


def create_topology(units, connections):
    return EnergyNetworkTopology.create(
        node_input_types={unit.get_id(): unit.get_input_energy_type() for unit in units},
        node_output_types={unit.get_id(): unit.get_output_energy_type() for unit in units},
        connections=[(source.get_id(), target.get_id()) for source, target in connections],
    )


class TestEnergyNetworkTopologyValidation:
    def test_rejects_incompatible_energy_types(self, energy_unit_factory_factory):
        source = FuelGasSource("source", output_energy=FuelGasRate(0))
        load = energy_unit_factory_factory(Consumer, "load", input_energy_type=ElectricalPower)

        with pytest.raises(InvalidEnergyNetworkError, match="Incompatible energy types"):
            create_topology([source, load], [(source, load)])

    def test_rejects_unknown_source(self, energy_unit_factory_factory):
        load = energy_unit_factory_factory(Consumer, "load", input_energy_type=ElectricalPower)
        source = FuelGasSource("source", output_energy=FuelGasRate(0))

        with pytest.raises(InvalidEnergyNetworkError, match="Unknown source"):
            EnergyNetworkTopology.create(
                node_input_types={load.get_id(): load.get_input_energy_type()},
                node_output_types={load.get_id(): load.get_output_energy_type()},
                connections=[(source.get_id(), load.get_id())],
            )

    def test_rejects_unknown_target(self, energy_unit_factory_factory):
        source = FuelGasSource("source", output_energy=FuelGasRate(0))
        target = energy_unit_factory_factory(Consumer, "target", input_energy_type=ElectricalPower)

        with pytest.raises(InvalidEnergyNetworkError, match="Unknown target"):
            EnergyNetworkTopology.create(
                node_input_types={source.get_id(): source.get_input_energy_type()},
                node_output_types={source.get_id(): source.get_output_energy_type()},
                connections=[(source.get_id(), target.get_id())],
            )

    def test_rejects_consumer_without_predecessor(self, energy_unit_factory_factory):
        load = energy_unit_factory_factory(Consumer, "load", input_energy_type=ElectricalPower)

        with pytest.raises(InvalidEnergyNetworkError, match="requires input energy but has no predecessor"):
            create_topology([load], [])

    def test_rejects_cycles(self, energy_unit_factory_factory):
        first = energy_unit_factory_factory(ElectricalCable, "first")
        second = energy_unit_factory_factory(ElectricalCable, "second")

        with pytest.raises(InvalidEnergyNetworkError, match="cannot be cyclic"):
            create_topology([first, second], [(first, second), (second, first)])

    def test_rejects_duplicate_connection_pair(self, energy_unit_factory_factory):
        source = ElectricalSource("source", output_energy=ElectricalPower(0))
        load = energy_unit_factory_factory(Consumer, "load", input_energy_type=ElectricalPower)

        with pytest.raises(InvalidEnergyNetworkError, match="Duplicate energy connection from"):
            create_topology([source, load], [(source, load), (source, load)])

    def test_rejects_duplicate_connection_id(self, energy_unit_factory_factory):
        source = ElectricalSource("source", output_energy=ElectricalPower(0))
        load = energy_unit_factory_factory(Consumer, "load", input_energy_type=ElectricalPower)
        connection_id = EnergyConnectionId(ElectricalSource._create_id())
        connection = EnergyConnection(connection_id, source.get_id(), load.get_id(), ElectricalPower)

        with pytest.raises(InvalidEnergyNetworkError, match="Duplicate energy connection ID"):
            EnergyNetworkTopology(nodes=[source.get_id(), load.get_id()], connections=[connection, connection])


class TestEnergyNetworkTopology:
    def test_exposes_typed_connections_in_topological_order(self, energy_unit_factory_factory):
        source = ElectricalSource("source", output_energy=ElectricalPower(0))
        cable = energy_unit_factory_factory(ElectricalCable, "cable")
        load = energy_unit_factory_factory(Consumer, "load", input_energy_type=ElectricalPower)

        topology = create_topology([source, cable, load], [(source, cable), (cable, load)])

        assert topology.get_topological_order() == (source.get_id(), cable.get_id(), load.get_id())
        assert topology.get_connections() == (
            topology.get_connection(source.get_id(), cable.get_id()),
            topology.get_connection(cable.get_id(), load.get_id()),
        )
        assert len({connection.id for connection in topology.get_connections()}) == len(topology.get_connections())
        assert all(connection.energy_type is ElectricalPower for connection in topology.get_connections())

    def test_connects_multiple_providers_to_junction(self, energy_unit_factory_factory, junction_factory_factory):
        grid = ElectricalSource("grid", output_energy=ElectricalPower(0))
        wind = ElectricalSource("wind", output_energy=ElectricalPower(0))
        bus = junction_factory_factory(
            ElectricalBus, "bus", dispatch_strategy=PriorityDispatch(order=(grid.get_id(), wind.get_id()))
        )
        load = energy_unit_factory_factory(Consumer, "load", input_energy_type=ElectricalPower)

        topology = create_topology([grid, wind, bus, load], [(grid, bus), (wind, bus), (bus, load)])

        assert topology.get_predecessors(bus.get_id()) == frozenset({grid.get_id(), wind.get_id()})
        assert topology.get_successors(bus.get_id()) == frozenset({load.get_id()})
        # Incoming connections are the topology's own connection records, so their IDs key the network's energy.
        assert set(topology.get_incoming_connections(bus.get_id())) == {
            topology.get_connection(grid.get_id(), bus.get_id()),
            topology.get_connection(wind.get_id(), bus.get_id()),
        }
        assert topology.get_incoming_connections(grid.get_id()) == ()
