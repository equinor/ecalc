import pytest

from libecalc.energy import Consumer, ElectricalPower, FuelGasRate
from libecalc.energy.energy_network_topology import EnergyConnection, EnergyConnectionId, EnergyNetworkTopology
from libecalc.energy.energy_units import (
    ElectricalBus,
    ElectricalCable,
    ElectricalSource,
    FuelGasSource,
)
from libecalc.energy.errors import InvalidEnergyNetworkError


def create_topology(units, connections):
    return EnergyNetworkTopology.create(
        node_input_types={unit.get_id(): unit.get_input_energy_type() for unit in units},
        node_output_types={unit.get_id(): unit.get_output_energy_type() for unit in units},
        connections=[(source.get_id(), target.get_id()) for source, target in connections],
    )


class TestEnergyNetworkTopologyValidation:
    def test_rejects_incompatible_energy_types(self):
        source = FuelGasSource("source", output_energy=FuelGasRate(0))
        load = Consumer("load", demand=ElectricalPower(0))

        with pytest.raises(InvalidEnergyNetworkError, match="Incompatible energy types"):
            create_topology([source, load], [(source, load)])

    def test_rejects_unknown_source(self):
        load = Consumer("load", demand=ElectricalPower(0))
        source = FuelGasSource("source", output_energy=FuelGasRate(0))

        with pytest.raises(InvalidEnergyNetworkError, match="Unknown source"):
            EnergyNetworkTopology.create(
                node_input_types={load.get_id(): load.get_input_energy_type()},
                node_output_types={load.get_id(): load.get_output_energy_type()},
                connections=[(source.get_id(), load.get_id())],
            )

    def test_rejects_unknown_target(self):
        source = FuelGasSource("source", output_energy=FuelGasRate(0))
        target = Consumer("target", demand=ElectricalPower(0))

        with pytest.raises(InvalidEnergyNetworkError, match="Unknown target"):
            EnergyNetworkTopology.create(
                node_input_types={source.get_id(): source.get_input_energy_type()},
                node_output_types={source.get_id(): source.get_output_energy_type()},
                connections=[(source.get_id(), target.get_id())],
            )

    def test_rejects_consumer_without_predecessor(self):
        load = Consumer("load", demand=ElectricalPower(0))

        with pytest.raises(InvalidEnergyNetworkError, match="requires input energy but has no predecessor"):
            create_topology([load], [])

    def test_rejects_cycles(self):
        first = ElectricalBus("first")
        second = ElectricalBus("second")

        with pytest.raises(InvalidEnergyNetworkError, match="cannot be cyclic"):
            create_topology([first, second], [(first, second), (second, first)])

    def test_rejects_duplicate_connection_pair(self):
        source = ElectricalSource("source", output_energy=ElectricalPower(0))
        load = Consumer("load", demand=ElectricalPower(0))

        with pytest.raises(InvalidEnergyNetworkError, match="Duplicate energy connection from"):
            create_topology([source, load], [(source, load), (source, load)])

    def test_rejects_duplicate_connection_id(self):
        source = ElectricalSource("source", output_energy=ElectricalPower(0))
        load = Consumer("load", demand=ElectricalPower(0))
        connection_id = EnergyConnectionId(ElectricalSource._create_id())
        connection = EnergyConnection(connection_id, source.get_id(), load.get_id(), ElectricalPower)

        with pytest.raises(InvalidEnergyNetworkError, match="Duplicate energy connection ID"):
            EnergyNetworkTopology(nodes=[source.get_id(), load.get_id()], connections=[connection, connection])


class TestEnergyNetworkTopology:
    def test_exposes_typed_connections_in_topological_order(self):
        source = ElectricalSource("source", output_energy=ElectricalPower(0))
        cable = ElectricalCable("cable", output_energy=ElectricalPower(0))
        load = Consumer("load", demand=ElectricalPower(0))

        topology = create_topology([source, cable, load], [(source, cable), (cable, load)])

        assert topology.get_topological_order() == (source.get_id(), cable.get_id(), load.get_id())
        assert topology.get_connections() == (
            topology.get_connection(source.get_id(), cable.get_id()),
            topology.get_connection(cable.get_id(), load.get_id()),
        )
        assert len({connection.id for connection in topology.get_connections()}) == len(topology.get_connections())
        assert all(connection.energy_type is ElectricalPower for connection in topology.get_connections())

    def test_connects_multiple_providers_to_junction(self):
        grid = ElectricalSource("grid", output_energy=ElectricalPower(0))
        wind = ElectricalSource("wind", output_energy=ElectricalPower(0))
        bus = ElectricalBus("bus")
        load = Consumer("load", demand=ElectricalPower(0))

        topology = create_topology([grid, wind, bus, load], [(grid, bus), (wind, bus), (bus, load)])

        assert topology.get_predecessors(bus.get_id()) == frozenset({grid.get_id(), wind.get_id()})
        assert topology.get_successors(bus.get_id()) == frozenset({load.get_id()})
