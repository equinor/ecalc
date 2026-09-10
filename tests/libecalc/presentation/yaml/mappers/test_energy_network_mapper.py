from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
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

    assert {connection.energy_type for connection in network.get_connections()} == {
        DieselRate,
        ElectricalPower,
        FuelGasRate,
        MechanicalPower,
    }
    assert len(network.get_topological_order()) == 13
    assert len(network.get_connections()) == 10
