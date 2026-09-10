from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.network_unit import EnergyNetworkUnit
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

    assert all(isinstance(node, EnergyNetworkUnit) for node in nodes.values())
    assert nodes["fuel"].get_input_energy_type() is None
    assert nodes["fuel"].get_output_energy_type() is FuelGasRate
    assert nodes["grid"].get_output_energy_type() is ElectricalPower
    assert nodes["diesel"].get_output_energy_type() is DieselRate
    assert nodes["genset"].get_input_energy_type() is FuelGasRate
    assert nodes["genset"].get_output_energy_type() is ElectricalPower
    assert nodes["turbine"].get_output_energy_type() is MechanicalPower
    assert nodes["motor"].get_input_energy_type() is ElectricalPower
    assert nodes["motor"].get_output_energy_type() is MechanicalPower
    assert nodes["cable"].get_input_energy_type() is ElectricalPower
    assert nodes["cable"].get_output_energy_type() is ElectricalPower
    assert nodes["bus"].get_input_energy_type() is ElectricalPower
    assert nodes["manifold"].get_output_energy_type() is FuelGasRate
    assert nodes["electrical_load"].get_output_energy_type() is None
    assert nodes["mechanical_load"].get_input_energy_type() is MechanicalPower
    assert nodes["fuel_load"].get_input_energy_type() is FuelGasRate
    assert nodes["diesel_load"].get_input_energy_type() is DieselRate
    assert network.get_predecessors(nodes["bus"].get_id()) == frozenset({nodes["cable"].get_id()})
    assert network.get_successors(nodes["fuel"].get_id()) == frozenset(
        {nodes["genset"].get_id(), nodes["turbine"].get_id(), nodes["manifold"].get_id()}
    )
