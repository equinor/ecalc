from io import StringIO

import pytest
import yaml

from libecalc.energy.energy_network_simulation import EnergyNetworkSimulation
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream

CURVE = {"POWER": [0, 4, 8], "FUEL": [0, 20000, 36000]}
# 6 MW sits between the points: fuel = 20000 + (36000 - 20000) / 2
EXPECTED_FUEL = 28000


def _generator_set_model_data(model, definitions, base_data_factory, load=6):
    data = base_data_factory()
    data["DEFINITIONS"] = definitions
    data["ENERGY_NETWORK"] = {
        "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
        "UNITS": [
            {"NAME": "genset", "TYPE": "GENERATOR_SET", "INPUT": "fuel", "MODEL": model},
            {"NAME": "load", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "genset", "LOAD": load},
        ],
    }
    return data


@pytest.fixture
def network_data_factory(yaml_asset_builder_factory, minimal_installation_yaml_factory, yaml_fuel_type_builder_factory):
    def create():
        asset = (
            yaml_asset_builder_factory()
            .with_test_data()
            .with_fuel_types([yaml_fuel_type_builder_factory().with_test_data().with_name("fuel").validate()])
            .with_installations([minimal_installation_yaml_factory(fuel_name="fuel")])
            .with_start("2020-01-01")
            .with_end("2021-01-01")
            .validate()
        )
        return asset.model_dump(by_alias=True, exclude_unset=True, mode="json")

    return create


def _model(data, yaml_model_factory, resources=None):
    return yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="generator_set_model"),
        resources=resources or {},
    )


def _run(model):
    topology, factories, consumers, _ = model.get_energy_network()
    simulation = EnergyNetworkSimulation(topology=topology, energy_unit_factories=factories)
    (load,) = consumers
    (period,) = load.demand.expression.get_periods()
    (load_connection,) = topology.get_incoming_connections(load.get_id())
    factories_by_name = {factory.get_name(): factory for factory in factories}
    fuel_connection = topology.get_connection(factories_by_name["fuel"].get_id(), factories_by_name["genset"].get_id())
    result = simulation.run({load_connection.id: load.get_demand(period)}, period=period)
    return result.get_energy()[fuel_connection.id].value, result.get_capacity_failures()


@pytest.mark.parametrize("source", ["reference", "inline", "file"])
def test_generator_set_fuel_follows_its_model(source, network_data_factory, yaml_model_factory):
    resources = {}
    curve = CURVE
    if source == "file":
        curve = {"FILE": "curve.csv"}
        resources["curve.csv"] = MemoryResource(data=[[0, 4, 8], [0, 20000, 36000]], headers=["POWER", "FUEL"])
    generator_set = {"CURVE": curve}
    if source == "inline":
        data = _generator_set_model_data(generator_set, {}, network_data_factory)
    else:
        data = _generator_set_model_data(
            "my_genset", {"GENERATOR_SETS": {"my_genset": generator_set}}, network_data_factory
        )

    fuel, _ = _run(_model(data, yaml_model_factory, resources))

    assert fuel == pytest.approx(EXPECTED_FUEL)


@pytest.mark.parametrize(("load", "exceeds_curve"), [(6, False), (10, True)])
def test_generator_set_curve_limit_reaches_the_simulation(
    load, exceeds_curve, network_data_factory, yaml_model_factory
):
    data = _generator_set_model_data({"CURVE": CURVE}, {}, network_data_factory, load=load)

    fuel, capacity_failures = _run(_model(data, yaml_model_factory))

    # Above the last point the highest fuel is used, as in the legacy generator set
    assert fuel == pytest.approx(EXPECTED_FUEL if load == 6 else 36000)
    assert bool(capacity_failures) is exceeds_curve


@pytest.mark.parametrize(
    ("definitions", "model_name", "message"),
    [
        ({}, "missing", "not a generator set"),
        ({"FLUIDS": {"not_a_generator_set": {"TYPE": "PREDEFINED"}}}, "not_a_generator_set", "not a generator set"),
    ],
    ids=["unknown_reference", "not_a_generator_set_definition"],
)
def test_generator_set_model_must_reference_a_generator_set_definition(
    definitions, model_name, message, network_data_factory, yaml_model_factory
):
    data = _generator_set_model_data(model_name, definitions, network_data_factory)

    with pytest.raises(ModelValidationException, match=f"{model_name}.*{message}") as exc_info:
        _model(data, yaml_model_factory).get_energy_network()
    assert exc_info.value.errors()[0].location.keys == ("ENERGY_NETWORK", "UNITS", 0, "MODEL")


def test_generator_set_definition_file_is_listed_as_facility_resource(
    network_data_factory, configuration_service_factory
):
    data = _generator_set_model_data(
        "my_genset", {"GENERATOR_SETS": {"my_genset": {"CURVE": {"FILE": "curve.csv"}}}}, network_data_factory
    )

    configuration = configuration_service_factory(
        ResourceStream(stream=StringIO(yaml.dump(data)), name="generator_set_model")
    ).get_configuration()

    assert "curve.csv" in configuration.facility_resource_names


@pytest.mark.parametrize(
    ("resources", "message"),
    [
        ({"curve.csv": MemoryResource(data=[[0, 4, 8], [0, 2, 3]], headers=["POWER", "FUEL_RATE"])}, "FUEL"),
        (
            {"curve.csv": MemoryResource(data=[[8, 4, 0], [3, 2, 0]], headers=["POWER", "FUEL"])},
            "FILE 'curve.csv'.*strictly increasing",
        ),
    ],
    ids=["missing_column", "descending_powers"],
)
def test_generator_set_file_errors_are_reported(resources, message, network_data_factory, yaml_model_factory):
    data = _generator_set_model_data(
        "my_genset", {"GENERATOR_SETS": {"my_genset": {"CURVE": {"FILE": "curve.csv"}}}}, network_data_factory
    )

    with pytest.raises(ModelValidationException, match=message):
        _model(data, yaml_model_factory, resources).get_energy_network()
