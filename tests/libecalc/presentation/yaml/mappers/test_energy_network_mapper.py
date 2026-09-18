from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.presentation.yaml.domain.energy import (
    TimeSeriesDieselConsumer,
    TimeSeriesDieselSourceFactory,
    TimeSeriesElectricalBus,
    TimeSeriesElectricalCableFactory,
    TimeSeriesElectricalConsumer,
    TimeSeriesElectricalMotorFactory,
    TimeSeriesElectricalSourceFactory,
    TimeSeriesFuelGasConsumer,
    TimeSeriesFuelGasManifold,
    TimeSeriesFuelGasSourceFactory,
    TimeSeriesGasTurbineFactory,
    TimeSeriesGeneratorSetFactory,
    TimeSeriesMechanicalConsumer,
)
from libecalc.presentation.yaml.mappers.energy_network_mapper import EnergyNetworkMapper
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlEnergyNetwork


def test_maps_sources_units_connections_and_expressions(expression_evaluator_factory, period):
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
                {"NAME": "motor", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "genset", "CAPACITY": 5, "EFFICIENCY": 0.9},
                {"NAME": "cable", "TYPE": "ELECTRICAL_CABLE", "INPUT": "grid", "CAPACITY": 4, "EFFICIENCY": 0.96},
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
    topology, energy_unit_factories, consumers, junctions = EnergyNetworkMapper().map_energy_network(
        yaml_network, expression_evaluator
    )

    assert {connection.energy_type for connection in topology.get_connections()} == {
        DieselRate,
        ElectricalPower,
        FuelGasRate,
        MechanicalPower,
    }
    assert len(topology.get_topological_order()) == 13
    assert len(topology.get_connections()) == 10

    # Sources, converters and transporters are returned as factories.
    assert [type(factory) for factory in energy_unit_factories] == [
        TimeSeriesFuelGasSourceFactory,
        TimeSeriesElectricalSourceFactory,
        TimeSeriesDieselSourceFactory,
        TimeSeriesGeneratorSetFactory,
        TimeSeriesGasTurbineFactory,
        TimeSeriesElectricalMotorFactory,
        TimeSeriesElectricalCableFactory,
    ]
    assert [factory.get_name() for factory in energy_unit_factories] == [
        "fuel",
        "grid",
        "diesel",
        "genset",
        "turbine",
        "motor",
        "cable",
    ]

    # Junctions are returned separately, not as factories.
    assert [type(junction) for junction in junctions] == [TimeSeriesElectricalBus, TimeSeriesFuelGasManifold]
    assert [junction.get_name() for junction in junctions] == ["bus", "manifold"]

    # Consumers are returned separately, not as factories.
    assert [type(consumer) for consumer in consumers] == [
        TimeSeriesElectricalConsumer,
        TimeSeriesMechanicalConsumer,
        TimeSeriesFuelGasConsumer,
        TimeSeriesDieselConsumer,
    ]
    assert [consumer.get_name() for consumer in consumers] == [
        "electrical_load",
        "mechanical_load",
        "fuel_load",
        "diesel_load",
    ]

    all_nodes = [*energy_unit_factories, *junctions, *consumers]
    assert {node.get_id() for node in all_nodes} == set(topology.get_nodes())

    factories_by_name = {factory.get_name(): factory for factory in energy_unit_factories}

    # Capacities are kept on the factories as time series expressions when provided in YAML.
    assert {name: factory.capacity.get_original_expression() for name, factory in factories_by_name.items()} == {
        "fuel": 100,
        "grid": 20,
        "diesel": 500,
        "genset": 10,
        "turbine": 15,
        "motor": 5,
        "cable": 4,
    }

    # Consumer demand is kept on the consumer dataclasses.
    consumers_by_name = {consumer.get_name(): consumer for consumer in consumers}
    assert consumers_by_name["electrical_load"].demand.get_original_expression() == 5
    assert consumers_by_name["mechanical_load"].demand.get_original_expression() == 2
    assert consumers_by_name["fuel_load"].demand.get_original_expression() == 10
    assert consumers_by_name["diesel_load"].demand.get_original_expression() == 20

    # Efficiency and loss fraction are kept on the relevant factories.
    assert factories_by_name["motor"].efficiency.get_original_expression() == 0.9
    assert factories_by_name["cable"].loss_fraction.get_original_expression() == "1 {-} (0.96)"
