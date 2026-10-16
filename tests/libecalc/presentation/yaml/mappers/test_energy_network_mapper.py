from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.energy.dispatch import PriorityDispatch
from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.presentation.yaml.domain.energy import (
    TimeSeriesConsumer,
    TimeSeriesElectricalCableFactory,
    TimeSeriesElectricalMotorFactory,
    TimeSeriesJunctionFactory,
    TimeSeriesSourceFactory,
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
                {"NAME": "backup_fuel", "TYPE": "FUEL_GAS_SOURCE", "CAPACITY": 50},
            ],
            "UNITS": [
                {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "CAPACITY": 10},
                {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel", "CAPACITY": 15},
                {"NAME": "motor", "TYPE": "ELECTRICAL_MOTOR", "INPUT": "genset", "CAPACITY": 5, "EFFICIENCY": 0.9},
                {"NAME": "cable", "TYPE": "ELECTRICAL_CABLE", "INPUT": "grid", "CAPACITY": 4, "EFFICIENCY": 0.96},
                {"NAME": "bus", "TYPE": "ELECTRICAL_BUS", "INPUT": ["cable", "grid"], "DISPATCH_STRATEGY": "PRIORITY"},
                {
                    "NAME": "manifold",
                    "TYPE": "FUEL_GAS_MANIFOLD",
                    "INPUT": ["fuel", "backup_fuel"],
                    "DISPATCH_STRATEGY": "PRIORITY",
                },
                {"NAME": "electrical_load", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "bus", "LOAD": 5},
                {"NAME": "mechanical_load", "TYPE": "MECHANICAL_CONSUMER", "INPUT": "motor", "LOAD": 2},
                {"NAME": "fuel_load", "TYPE": "FUEL_GAS_CONSUMER", "INPUT": "manifold", "RATE": 10},
                {"NAME": "diesel_load", "TYPE": "DIESEL_CONSUMER", "INPUT": "diesel", "RATE": 20},
            ],
        }
    )

    expression_evaluator = expression_evaluator_factory.from_periods(periods=[period])
    topology, energy_unit_factories, consumers = EnergyNetworkMapper().map_energy_network(
        yaml_network, expression_evaluator
    )

    assert {connection.energy_type for connection in topology.get_connections()} == {
        DieselRate,
        ElectricalPower,
        FuelGasRate,
        MechanicalPower,
    }

    assert all(
        isinstance(factory, TimeSeriesSourceFactory)
        for factory in energy_unit_factories
        if factory.get_name() in {"fuel", "grid", "diesel", "backup_fuel"}
    )

    # Consumers are returned separately, not as factories.
    assert all(isinstance(consumer, TimeSeriesConsumer) for consumer in consumers)

    # Each consumer's input energy type is derived from its connection, per YAML consumer type.
    consumer_energy_types = {
        consumer.get_name(): next(
            connection.energy_type
            for connection in topology.get_connections()
            if connection.target_id == consumer.get_id()
        )
        for consumer in consumers
    }
    assert consumer_energy_types == {
        "electrical_load": ElectricalPower,
        "mechanical_load": MechanicalPower,
        "fuel_load": FuelGasRate,
        "diesel_load": DieselRate,
    }

    all_nodes = [*energy_unit_factories, *consumers]
    assert {node.get_id() for node in all_nodes} == set(topology.get_nodes())

    factories_by_name = {factory.get_name(): factory for factory in energy_unit_factories}

    expected_capacities = {
        "fuel": 100,
        "grid": 20,
        "diesel": 500,
        "backup_fuel": 50,
        "genset": 10,
        "turbine": 15,
        "motor": 5,
        "cable": 4,
    }
    for name, capacity in expected_capacities.items():
        capacity_expression = factories_by_name[name].capacity
        assert capacity_expression is not None
        assert capacity_expression.get_original_expression() == capacity

    # Consumer demand is a callable producing the appropriate Energy type per period.
    consumers_by_name = {consumer.get_name(): consumer for consumer in consumers}
    assert consumers_by_name["electrical_load"].get_demand(period) == ElectricalPower(5)
    assert consumers_by_name["mechanical_load"].get_demand(period) == MechanicalPower(2)
    assert consumers_by_name["fuel_load"].get_demand(period) == FuelGasRate(10)
    assert consumers_by_name["diesel_load"].get_demand(period) == DieselRate(20)

    # Efficiency and loss fraction are kept on the relevant factories.
    motor = factories_by_name["motor"]
    cable = factories_by_name["cable"]
    assert isinstance(motor, TimeSeriesElectricalMotorFactory)
    assert isinstance(cable, TimeSeriesElectricalCableFactory)
    assert motor.efficiency is not None
    assert motor.efficiency.get_original_expression() == 0.9
    assert cable.loss_fraction is not None
    assert cable.loss_fraction.get_original_expression() == "1 {-} (0.96)"


SHORE_AND_WIND = {
    "SOURCES": [
        {"NAME": "shore", "TYPE": "ELECTRICAL_SOURCE", "CAPACITY": 20},
        {"NAME": "wind", "TYPE": "ELECTRICAL_SOURCE", "CAPACITY": 4.4},
    ],
    "UNITS": [
        {"NAME": "load", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "bus", "LOAD": "SIM1;LOAD"},
        {
            "NAME": "bus",
            "TYPE": "ELECTRICAL_BUS",
            "INPUT": [{"NAME": "cable", "CAPACITY": "SIM1;CABLE_AT_BUS"}, "wind"],
            "DISPATCH_STRATEGY": "PRIORITY",
        },
        {"NAME": "cable", "TYPE": "ELECTRICAL_CABLE", "INPUT": "shore", "EFFICIENCY": 0.97},
    ],
}


FIRST_PERIOD = Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))
SECOND_PERIOD = Period(start=datetime(2021, 1, 1), end=datetime(2022, 1, 1))


@pytest.mark.parametrize(("period", "cable_to_bus"), [(FIRST_PERIOD, 19.4), (SECOND_PERIOD, 15)])
def test_junction_input_capacity_is_evaluated_per_period(expression_evaluator_factory, period, cable_to_bus):
    expression_evaluator = expression_evaluator_factory.from_periods(
        periods=[FIRST_PERIOD, SECOND_PERIOD],
        variables={"SIM1;LOAD": [22, 20], "SIM1;CABLE_AT_BUS": [19.4, 15]},
    )
    topology, energy_unit_factories, _consumers = EnergyNetworkMapper().map_energy_network(
        YamlEnergyNetwork.model_validate(SHORE_AND_WIND), expression_evaluator
    )
    factories_by_name = {factory.get_name(): factory for factory in energy_unit_factories}
    bus = factories_by_name["bus"]
    assert isinstance(bus, TimeSeriesJunctionFactory)

    cable_id, wind_id = factories_by_name["cable"].get_id(), factories_by_name["wind"].get_id()
    assert bus.dispatch_strategy == PriorityDispatch(order=(cable_id, wind_id))
    assert bus.input_capacities[cable_id].get_value(period) == pytest.approx(cable_to_bus)
