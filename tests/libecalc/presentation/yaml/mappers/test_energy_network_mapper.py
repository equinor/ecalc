from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
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


def test_maps_sources_units_connections_and_consumer_expressions(expression_evaluator_factory, period):
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

    expression_evaluator = expression_evaluator_factory.from_periods(periods=[period])
    network, energy_units, consumer_expressions = EnergyNetworkMapper().map_energy_network(
        yaml_network, expression_evaluator
    )

    assert {connection.energy_type for connection in network.get_connections()} == {
        DieselRate,
        ElectricalPower,
        FuelGasRate,
        MechanicalPower,
    }
    assert len(network.get_topological_order()) == 13
    assert len(network.get_connections()) == 10
    assert [type(energy_unit) for energy_unit in energy_units] == [
        FuelGasSource,
        ElectricalSource,
        DieselSource,
        GeneratorSet,
        GasTurbine,
        ElectricalMotor,
        ElectricalCable,
        ElectricalBus,
        FuelGasManifold,
        ElectricalConsumer,
        MechanicalConsumer,
        FuelGasConsumer,
        DieselConsumer,
    ]
    assert [energy_unit.get_name() for energy_unit in energy_units] == [
        "fuel",
        "grid",
        "diesel",
        "genset",
        "turbine",
        "motor",
        "cable",
        "bus",
        "manifold",
        "electrical_load",
        "mechanical_load",
        "fuel_load",
        "diesel_load",
    ]
    assert {energy_unit.get_id() for energy_unit in energy_units} == set(network.get_nodes())
    consumer_ids_by_name = {energy_unit.get_name(): energy_unit.get_id() for energy_unit in energy_units}
    assert {
        consumer_ids_by_name["electrical_load"]: 5,
        consumer_ids_by_name["mechanical_load"]: 2,
        consumer_ids_by_name["fuel_load"]: 10,
        consumer_ids_by_name["diesel_load"]: 20,
    } == {
        energy_unit_id: expression.get_original_expression()
        for energy_unit_id, expression in consumer_expressions.items()
    }
