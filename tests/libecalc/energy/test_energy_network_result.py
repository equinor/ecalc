import pytest

from libecalc.energy import ElectricalPower
from libecalc.energy.energy_network_simulation import EnergyNetworkSimulation
from libecalc.energy.energy_network_topology import EnergyNetworkTopology
from libecalc.energy.energy_units import ElectricalConsumer, ElectricalSource


def test_energy_network_contains_simulation_state():
    source = ElectricalSource("source")
    consumer = ElectricalConsumer("consumer")
    topology = EnergyNetworkTopology.create(
        node_input_types={
            source.get_id(): source.get_input_energy_type(),
            consumer.get_id(): consumer.get_input_energy_type(),
        },
        node_output_types={
            source.get_id(): source.get_output_energy_type(),
            consumer.get_id(): consumer.get_output_energy_type(),
        },
        connections=[(source.get_id(), consumer.get_id())],
    )
    connection = topology.get_connection(source.get_id(), consumer.get_id())
    connection_demands = {connection.id: ElectricalPower(5)}
    capacities = {source.get_id(): ElectricalPower(10)}

    network = EnergyNetworkSimulation(topology=topology, energy_units=[source, consumer]).run(
        connection_demands,
        capacities,
    )
    assert network.topology is topology
    assert network.get_energy_units() == (source, consumer)
    assert network.get_energy_unit(source.get_id()) is source
    assert network.get_consumer_demand(consumer.get_id()) == ElectricalPower(5)
    assert network.connection_demands[connection.id] == ElectricalPower(5)
    assert network.capacities[source.get_id()] == ElectricalPower(10)
    assert network.get_connection_energy(connection.id) == ElectricalPower(5)
    assert network.get_capacity(source.get_id()) == ElectricalPower(10)
    assert network.get_capacity(consumer.get_id()) is None
    assert network.get_capacity_failure(source.get_id()) is None
    assert not network.get_capacity_failures()
    assert network.is_feasible()

    with pytest.raises(KeyError, match="No consumer demand found"):
        network.get_consumer_demand(source.get_id())
