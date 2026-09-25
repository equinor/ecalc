from io import StringIO

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.energy_types import ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.presentation.yaml.domain.energy import TimeSeriesGasTurbineFactory
from libecalc.presentation.yaml.mappers.energy_network_mapper import EnergyNetworkMapper
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlEnergyNetwork


def _network(compressor_input: str, **compressor_fields) -> YamlEnergyNetwork:
    return YamlEnergyNetwork.model_validate(
        {
            "SOURCES": [
                {"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"},
            ],
            "UNITS": [
                {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "fuel"},
                {
                    "NAME": "compressor",
                    "TYPE": "COMPRESSOR_SAMPLED",
                    "INPUT": compressor_input,
                    "FILE": "compressor.csv",
                    "RATE": 2500,
                    **compressor_fields,
                },
            ],
        }
    )


def _connections_by_name(topology, nodes) -> set[tuple[str, str]]:
    names = {node.get_id(): node.get_name() for node in nodes}
    return {(names[c.source_id], names[c.target_id]) for c in topology.get_connections()}


class TestMapperExpansion:
    def test_fuel_only_maps_to_fuel_gas_consumer(
        self, expression_evaluator_factory, period, make_resource, rates, fuel
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        topology, factories, consumers = EnergyNetworkMapper().map_energy_network(
            _network("fuel"), evaluator, resources={"compressor.csv": make_resource(RATE=rates, FUEL=fuel)}
        )

        (compressor,) = consumers
        assert compressor.get_name() == "compressor"
        assert compressor.get_input_energy_type() is FuelGasRate
        assert compressor.get_demand(period) == FuelGasRate(25000)
        assert len(topology.get_nodes()) == 3
        assert _connections_by_name(topology, [*factories, *consumers]) == {
            ("fuel", "genset"),
            ("fuel", "compressor"),
        }

    def test_power_only_maps_to_consumer_typed_after_input(
        self, expression_evaluator_factory, period, make_resource, rates, power
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        topology, factories, consumers = EnergyNetworkMapper().map_energy_network(
            _network("genset"), evaluator, resources={"compressor.csv": make_resource(RATE=rates, POWER=power)}
        )

        (compressor,) = consumers
        assert compressor.get_input_energy_type() is ElectricalPower
        assert compressor.get_demand(period) == ElectricalPower(12.5)
        assert len(topology.get_nodes()) == 3
        assert ("genset", "compressor") in _connections_by_name(topology, [*factories, *consumers])

    def test_fuel_and_power_generates_turbine_fed_by_declared_input(
        self, expression_evaluator_factory, period, make_resource, rates, fuel, power
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        topology, factories, consumers = EnergyNetworkMapper().map_energy_network(
            _network("fuel"),
            evaluator,
            resources={"compressor.csv": make_resource(RATE=rates, FUEL=fuel, POWER=power)},
        )

        (compressor,) = consumers
        assert compressor.get_input_energy_type() is MechanicalPower
        assert compressor.get_demand(period) == MechanicalPower(12.5)

        turbine = next(f for f in factories if f.get_name() == "compressor turbine")
        assert isinstance(turbine, TimeSeriesGasTurbineFactory)
        assert turbine.power_to_fuel(12.5) == pytest.approx(25000)

        assert len(topology.get_nodes()) == 4
        connections = _connections_by_name(topology, [*factories, *consumers])
        assert ("fuel", "compressor turbine") in connections
        assert ("compressor turbine", "compressor") in connections
        assert ("fuel", "compressor") not in connections
        assert topology.get_connection(turbine.get_id(), compressor.get_id()).energy_type is MechanicalPower

    def test_missing_resource_rejected(self, expression_evaluator_factory, period):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        with pytest.raises(EcalcValidationException, match="FILE 'compressor.csv' not found"):
            EnergyNetworkMapper().map_energy_network(_network("fuel"), evaluator, resources={})

    def test_fuel_only_on_electrical_input_rejected(
        self, expression_evaluator_factory, period, make_resource, rates, fuel
    ):
        evaluator = expression_evaluator_factory.from_periods(periods=[period])
        with pytest.raises(EcalcValidationException, match="must be fed FuelGasRate"):
            EnergyNetworkMapper().map_energy_network(
                _network("genset"), evaluator, resources={"compressor.csv": make_resource(RATE=rates, FUEL=fuel)}
            )


MODEL_YAML = """
START: 2020-01-01
END: 2021-01-01
FUEL_TYPES:
  - NAME: fuel_gas
    EMISSIONS:
      - NAME: CO2
        FACTOR: 2.2
INSTALLATIONS:
  - NAME: installation
    FUEL: fuel_gas
    FUELCONSUMERS:
      - NAME: flare
        CATEGORY: FLARE
        ENERGY_USAGE_MODEL:
          TYPE: DIRECT
          FUELRATE: 10
ENERGY_NETWORK:
  SOURCES:
    - NAME: fuel
      TYPE: FUEL_GAS_SOURCE
  UNITS:
    - NAME: compressor
      TYPE: COMPRESSOR_SAMPLED
      INPUT: fuel
      FILE: {file}
      RATE: 1500
"""


def _yaml_model(yaml_model_factory, resources: dict[str, MemoryResource], file: str = "compressor.csv"):
    stream = ResourceStream(name="model.yaml", stream=StringIO(MODEL_YAML.format(file=file)))
    return yaml_model_factory(configuration=stream, resources=resources)


class TestEndToEnd:
    def test_fuel_and_power(self, yaml_model_factory, make_resource, rates, fuel, power):
        model = _yaml_model(yaml_model_factory, {"compressor.csv": make_resource(RATE=rates, FUEL=fuel, POWER=power)})
        topology, factories, consumers = model.get_energy_network()

        assert topology is not None
        assert len(topology.get_nodes()) == 3
        assert len(topology.get_connections()) == 2
        assert [f.get_name() for f in factories] == ["fuel", "compressor turbine"]
        assert consumers[0].get_demand(model.get_periods()[0]) == MechanicalPower(7.5)

    def test_unknown_file_reported_at_validation(self, yaml_model_factory):
        model = _yaml_model(yaml_model_factory, {}, file="missing.csv")
        with pytest.raises(ModelValidationException, match="resource not found, got 'missing.csv'"):
            model.validate_for_run()

    def test_invalid_table_reported_as_model_validation_error(self, yaml_model_factory, make_resource, rates, fuel):
        model = _yaml_model(
            yaml_model_factory, {"compressor.csv": make_resource(RATE=rates, FUEL=fuel, POWER=[5.0, 5.0, 15.0])}
        )
        with pytest.raises(ModelValidationException, match="strictly monotonic"):
            model.get_energy_network()
