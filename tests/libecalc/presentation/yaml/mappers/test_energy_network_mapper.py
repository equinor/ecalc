from libecalc.energy.energy_units import (
    DieselConsumer,
    DieselSource,
    ElectricalBus,
    ElectricalCable,
    ElectricalConsumer,
    ElectricalMotor,
    ElectricalSource,
    FuelGasConsumer,
    FuelGasManifold,
    FuelGasSource,
    GasTurbine,
    GeneratorSet,
    MechanicalConsumer,
)
from libecalc.presentation.yaml.mappers.energy_network_mapper import EnergyNetworkMapper
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlEnergyNetwork


def test_maps_sources_units_and_connections():
    yaml_network = YamlEnergyNetwork.model_validate(
        {
            "SOURCES": [
                {"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE", "CAPACITY": 100},
                {"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE", "CAPACITY": 20},
                {"NAME": "diesel", "TYPE": "DIESEL_SOURCE", "CAPACITY": 500},
            ],
            "UNITS": [
                {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "CAPACITY": 10},
                {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel", "CAPACITY": 15},
                {"NAME": "motor", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "genset", "CAPACITY": 5},
                {"NAME": "cable", "TYPE": "ELECTRICAL_CABLE", "INPUT": "grid"},
                {"NAME": "bus", "TYPE": "ELECTRICAL_BUS", "INPUT": ["cable"]},
                {"NAME": "manifold", "TYPE": "FUEL_GAS_MANIFOLD", "INPUT": ["fuel"]},
                {"NAME": "electrical_load", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "bus", "LOAD": 5},
                {"NAME": "mechanical_load", "TYPE": "MECHANICAL_CONSUMER", "INPUT": "motor", "LOAD": 2},
                {"NAME": "fuel_load", "TYPE": "FUEL_GAS_CONSUMER", "INPUT": "manifold", "RATE": 10},
                {"NAME": "diesel_load", "TYPE": "DIESEL_CONSUMER", "INPUT": "diesel", "RATE": 20},
            ],
        }
    )

    network = EnergyNetworkMapper().map_energy_network(yaml_network)
    nodes = {node.get_name(): node for node in network.get_nodes()}

    assert isinstance(nodes["fuel"], FuelGasSource)
    assert isinstance(nodes["grid"], ElectricalSource)
    assert isinstance(nodes["diesel"], DieselSource)
    assert isinstance(nodes["genset"], GeneratorSet)
    assert isinstance(nodes["turbine"], GasTurbine)
    assert isinstance(nodes["motor"], ElectricalMotor)
    assert isinstance(nodes["cable"], ElectricalCable)
    assert isinstance(nodes["bus"], ElectricalBus)
    assert isinstance(nodes["manifold"], FuelGasManifold)
    assert isinstance(nodes["electrical_load"], ElectricalConsumer)
    assert isinstance(nodes["mechanical_load"], MechanicalConsumer)
    assert isinstance(nodes["fuel_load"], FuelGasConsumer)
    assert isinstance(nodes["diesel_load"], DieselConsumer)
    assert network.get_predecessors(nodes["bus"].get_id()) == frozenset({nodes["cable"].get_id()})
    assert network.get_successors(nodes["fuel"].get_id()) == frozenset(
        {nodes["genset"].get_id(), nodes["turbine"].get_id(), nodes["manifold"].get_id()}
    )
