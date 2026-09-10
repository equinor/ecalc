import pytest

from libecalc.energy import ElectricalPower
from libecalc.energy.energy_units import (
    ElectricalBus,
    ElectricalCable,
    ElectricalConsumer,
    ElectricalSource,
    FuelGasSource,
)
from libecalc.energy.errors import InvalidEnergyNetworkError
from libecalc.energy.network import EnergyNetwork


def create_network(units, connections):
    return EnergyNetwork.create(
        node_input_types={unit.get_id(): unit.get_input_energy_type() for unit in units},
        node_output_types={unit.get_id(): unit.get_output_energy_type() for unit in units},
        connections=[(source.get_id(), target.get_id()) for source, target in connections],
    )


class TestEnergyNetworkValidation:
    def test_rejects_incompatible_energy_types(self):
        source = FuelGasSource("source")
        load = ElectricalConsumer("load")

        with pytest.raises(InvalidEnergyNetworkError, match="Incompatible energy types"):
            create_network([source, load], [(source, load)])

    def test_rejects_unknown_source(self):
        load = ElectricalConsumer("load")
        source = FuelGasSource("source")

        with pytest.raises(InvalidEnergyNetworkError, match="Unknown source"):
            EnergyNetwork.create(
                node_input_types={load.get_id(): load.get_input_energy_type()},
                node_output_types={load.get_id(): load.get_output_energy_type()},
                connections=[(source.get_id(), load.get_id())],
            )

    def test_rejects_unknown_target(self):
        source = FuelGasSource("source")
        target = ElectricalConsumer("target")

        with pytest.raises(InvalidEnergyNetworkError, match="Unknown target"):
            EnergyNetwork.create(
                node_input_types={source.get_id(): source.get_input_energy_type()},
                node_output_types={source.get_id(): source.get_output_energy_type()},
                connections=[(source.get_id(), target.get_id())],
            )

    def test_rejects_consumer_without_predecessor(self):
        load = ElectricalConsumer("load")

        with pytest.raises(InvalidEnergyNetworkError, match="requires input energy but has no predecessor"):
            create_network([load], [])

    def test_rejects_cycles(self):
        first = ElectricalBus("first")
        second = ElectricalBus("second")

        with pytest.raises(InvalidEnergyNetworkError, match="cannot be cyclic"):
            create_network([first, second], [(first, second), (second, first)])


class TestEnergyNetworkTopology:
    def test_exposes_typed_connections_in_topological_order(self):
        source = ElectricalSource("source")
        cable = ElectricalCable("cable")
        load = ElectricalConsumer("load")

        network = create_network([source, cable, load], [(source, cable), (cable, load)])

        assert network.get_topological_order() == (source.get_id(), cable.get_id(), load.get_id())
        assert network.get_connections() == (
            network.get_connection(source.get_id(), cable.get_id()),
            network.get_connection(cable.get_id(), load.get_id()),
        )
        assert len({connection.id for connection in network.get_connections()}) == len(network.get_connections())
        assert all(connection.energy_type is ElectricalPower for connection in network.get_connections())

    def test_connects_multiple_providers_to_junction(self):
        grid = ElectricalSource("grid")
        wind = ElectricalSource("wind")
        bus = ElectricalBus("bus")
        load = ElectricalConsumer("load")

        network = create_network([grid, wind, bus, load], [(grid, bus), (wind, bus), (bus, load)])

        assert network.get_predecessors(bus.get_id()) == frozenset({grid.get_id(), wind.get_id()})
        assert network.get_successors(bus.get_id()) == frozenset({load.get_id()})
