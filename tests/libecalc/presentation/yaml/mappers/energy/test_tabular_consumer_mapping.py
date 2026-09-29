import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.presentation.yaml.mappers.energy_network_mapper import EnergyNetworkMapper
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlEnergyNetwork


def _network(consumer_input: str, variables: dict[str, float | str]) -> YamlEnergyNetwork:
    return YamlEnergyNetwork.model_validate(
        {
            "SOURCES": [
                {"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"},
                {"NAME": "diesel", "TYPE": "DIESEL_SOURCE"},
            ],
            "UNITS": [
                {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "fuel"},
                {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel"},
                {
                    "NAME": "consumer",
                    "TYPE": "TABULAR_CONSUMER",
                    "INPUT": consumer_input,
                    "FILE": "table.csv",
                    "VARIABLES": variables,
                },
            ],
        }
    )


def _map(evaluator, network, resource):
    return EnergyNetworkMapper().map_energy_network(network, evaluator, resources={"table.csv": resource})


@pytest.fixture
def evaluator(expression_evaluator_factory, period):
    return expression_evaluator_factory.from_periods(periods=[period])


@pytest.mark.parametrize(("input_name", "energy_type"), [("fuel", FuelGasRate), ("diesel", DieselRate)])
def test_fuel_table_is_typed_after_input(evaluator, period, make_resource, input_name, energy_type):
    resource = make_resource(RATE=[1.0, 2.0, 3.0], FUEL=[10.0, 20.0, 30.0])
    _, _, (consumer,) = _map(evaluator, _network(input_name, {"RATE": 2.5}), resource)

    assert consumer.get_input_energy_type() is energy_type
    assert consumer.get_demand(period) == energy_type(25.0)


@pytest.mark.parametrize(("input_name", "energy_type"), [("genset", ElectricalPower), ("turbine", MechanicalPower)])
def test_power_table_is_typed_after_input(evaluator, period, make_resource, input_name, energy_type):
    resource = make_resource(RATE=[1.0, 2.0, 3.0], POWER=[1.0, 2.0, 3.0])
    _, _, (consumer,) = _map(evaluator, _network(input_name, {"RATE": 1.5}), resource)

    assert consumer.get_input_energy_type() is energy_type
    assert consumer.get_demand(period) == energy_type(1.5)


def test_multiple_variables(evaluator, period, make_resource):
    resource = make_resource(RATE=[1.0, 1.0, 2.0, 2.0], PRESSURE=[10.0, 20.0, 10.0, 20.0], FUEL=[1.0, 2.0, 3.0, 4.0])
    _, _, (consumer,) = _map(evaluator, _network("fuel", {"RATE": 1.5, "PRESSURE": 15}), resource)

    assert consumer.get_demand(period) == FuelGasRate(2.5)


def test_outside_table_range_raises(evaluator, period, make_resource):
    resource = make_resource(RATE=[1.0, 2.0], FUEL=[10.0, 20.0])
    _, _, (consumer,) = _map(evaluator, _network("fuel", {"RATE": 5}), resource)

    with pytest.raises(InvalidEnergyNetworkInputError):
        consumer.get_demand(period)


@pytest.mark.parametrize(
    ("consumer_input", "resource_columns", "variables", "message"),
    [
        ("genset", {"RATE": [1.0, 2.0], "FUEL": [1.0, 2.0]}, {"RATE": 1}, "must be fed FuelGasRate or DieselRate"),
        ("fuel", {"RATE": [1.0, 2.0], "POWER": [1.0, 2.0]}, {"RATE": 1}, "must be fed electrical or mechanical"),
        ("fuel", {"RATE": [1.0, 2.0]}, {"RATE": 1}, "must have a FUEL or POWER column"),
        ("genset", {"RATE": [1.0, 2.0], "FUEL": [1.0, 2.0], "POWER": [1.0, 2.0]}, {"RATE": 1}, "not both"),
        ("fuel", {"RATE": [1.0, 2.0], "FUEL": [1.0, 2.0]}, {"RATE": 1, "OTHER": 1}, "OTHER given, but not tabulated"),
        ("fuel", {"RATE": [1.0, 2.0], "P": [1.0, 2.0], "FUEL": [1.0, 2.0]}, {"RATE": 1}, "tabulates P, which must"),
    ],
)
def test_invalid_combinations(evaluator, make_resource, consumer_input, resource_columns, variables, message):
    with pytest.raises(EcalcValidationException, match=message):
        _map(evaluator, _network(consumer_input, variables), make_resource(**resource_columns))


def test_invalid_table_is_a_validation_error(evaluator, make_resource):
    resource = make_resource(RATE=[1.0, 2.0, 3.0], PRESSURE=[5.0, 5.0, 5.0], FUEL=[1.0, 2.0, 3.0])
    with pytest.raises(EcalcValidationException, match="invalid tabular file"):
        _map(evaluator, _network("fuel", {"RATE": 1.5, "PRESSURE": 5}), resource)


def test_missing_resource_raises(evaluator):
    with pytest.raises(EcalcValidationException, match="not found"):
        EnergyNetworkMapper().map_energy_network(_network("fuel", {"RATE": 1}), evaluator, resources={})
