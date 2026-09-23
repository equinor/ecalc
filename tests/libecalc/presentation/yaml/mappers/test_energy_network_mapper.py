from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.energy.energy_network_simulation import EnergyNetworkSimulation
from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
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
        assert factories_by_name[name].capacity.get_original_expression() == capacity

    # Consumer demand is kept on the consumer dataclasses.
    consumers_by_name = {consumer.get_name(): consumer for consumer in consumers}
    assert consumers_by_name["electrical_load"].demand.get_original_expression() == 5
    assert consumers_by_name["mechanical_load"].demand.get_original_expression() == 2
    assert consumers_by_name["fuel_load"].demand.get_original_expression() == 10
    assert consumers_by_name["diesel_load"].demand.get_original_expression() == 20

    # Efficiency and loss fraction are kept on the relevant factories.
    assert factories_by_name["motor"].efficiency.get_original_expression() == 0.9
    assert factories_by_name["cable"].loss_fraction.get_original_expression() == "1 {-} (0.96)"


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


class TestMappedNetworkSimulation:
    def test_dispatches_each_period_with_that_periods_input_capacity(self, expression_evaluator_factory):
        """Declaration order must not affect priority or per-period dispatch limits."""
        first_period = Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))
        second_period = Period(start=datetime(2021, 1, 1), end=datetime(2022, 1, 1))
        expression_evaluator = expression_evaluator_factory.from_periods(
            periods=[first_period, second_period],
            variables={"SIM1;LOAD": [22, 20], "SIM1;CABLE_AT_BUS": [19.4, 15]},
        )
        topology, energy_unit_factories, consumers = EnergyNetworkMapper().map_energy_network(
            YamlEnergyNetwork.model_validate(SHORE_AND_WIND), expression_evaluator
        )
        simulation = EnergyNetworkSimulation(topology=topology, energy_unit_factories=energy_unit_factories)
        ids_by_name = {node.get_name(): node.get_id() for node in [*energy_unit_factories, *consumers]}

        def run(period: Period):
            connection_demands = {}
            for consumer in consumers:
                (connection,) = topology.get_incoming_connections(consumer.get_id())
                assert consumer.demand is not None
                connection_demands[connection.id] = ElectricalPower(consumer.demand.get_value(period))
            return simulation.run(connection_demands, period=period)

        def energy(network, source: str, target: str) -> float:
            return network.get_energy()[topology.get_connection(ids_by_name[source], ids_by_name[target]).id].value

        first = run(first_period)
        second = run(second_period)

        # 19.4 MW at the bus is what 20 MW from shore delivers through the 97 % cable, so nothing is overloaded.
        assert energy(first, "cable", "bus") == pytest.approx(19.4)
        assert energy(first, "wind", "bus") == pytest.approx(2.6)
        assert energy(first, "shore", "cable") == pytest.approx(20)
        assert not first.get_capacity_failures()

        # A lower limit at the bus moves demand onto wind, which is then over its own 4.4 MW rating.
        assert energy(second, "cable", "bus") == pytest.approx(15)
        assert energy(second, "wind", "bus") == pytest.approx(5)
        assert set(second.get_capacity_failures()) == {ids_by_name["wind"]}
