from io import StringIO

import pytest
import yaml

from libecalc.energy.energy_network_simulation import EnergyNetworkSimulation
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.testing.yaml_builder import YamlTimeSeriesBuilder


def test_returns_nothing_without_an_energy_network(minimal_model_yaml_factory, yaml_model_factory):
    model = yaml_model_factory(configuration=minimal_model_yaml_factory().get_configuration(), resources={})

    assert model.get_energy_network() == (None, (), (), [])


def test_input_capacity_reads_a_time_series_referenced_only_by_the_junction(
    yaml_asset_builder_factory,
    minimal_installation_yaml_factory,
    yaml_fuel_type_builder_factory,
    yaml_model_factory,
):
    """The evaluator only loads referenced time series, so a reference nested in INPUT must be found and used."""
    asset = (
        yaml_asset_builder_factory()
        .with_test_data()
        .with_fuel_types([yaml_fuel_type_builder_factory().with_test_data().with_name("fuel").validate()])
        .with_installations([minimal_installation_yaml_factory(fuel_name="fuel")])
        .with_time_series([YamlTimeSeriesBuilder().with_name("SIM1").with_type("DEFAULT").with_file("SIM1").validate()])
        .with_start("2020-01-01")
        .with_end("2022-01-01")
        .validate()
    )
    data = asset.model_dump(by_alias=True, exclude_unset=True, mode="json")
    data["ENERGY_NETWORK"] = {
        "SOURCES": [{"NAME": "grid", "TYPE": "ELECTRICAL_SOURCE"}, {"NAME": "wind", "TYPE": "ELECTRICAL_SOURCE"}],
        "UNITS": [
            {
                "NAME": "bus",
                "TYPE": "ELECTRICAL_BUS",
                "INPUT": [{"NAME": "grid", "CAPACITY": "SIM1;GRID_LIMIT"}, "wind"],
                "DISPATCH_STRATEGY": "PRIORITY",
            },
            {"NAME": "load", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "bus", "LOAD": 10},
        ],
    }
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="energy_network_model"),
        resources={
            "SIM1": MemoryResource(
                data=[["2020-01-01", "2021-01-01"], [6, 8]],
                headers=["DATE", "GRID_LIMIT"],
            )
        },
    )

    topology, energy_unit_factories, consumers, _periods = model.get_energy_network()

    assert topology is not None
    simulation = EnergyNetworkSimulation(topology=topology, energy_unit_factories=energy_unit_factories)
    (load,) = consumers
    assert load.demand.expression is not None
    (load_connection,) = topology.get_incoming_connections(load.get_id())
    factories_by_name = {factory.get_name(): factory for factory in energy_unit_factories}
    grid_to_bus = topology.get_connection(factories_by_name["grid"].get_id(), factories_by_name["bus"].get_id())

    grid_shares = [
        simulation.run(
            {load_connection.id: load.get_demand(period)},
            period=period,
        )
        .get_energy()[grid_to_bus.id]
        .value
        for period in load.demand.expression.get_periods()
    ]

    assert grid_shares == pytest.approx([6, 8])


CURVE = {"LOAD": [2, 4, 8], "EFFICIENCY": [0.1, 0.2, 0.3]}
TURBINE_LHV = 38
# 5 MW sits between the points: efficiency 0.225, so fuel = 5 * 86400 / 38 / 0.225
EXPECTED_FUEL = 5 * 86400 / TURBINE_LHV / 0.225


def _turbine_model_data(model, definitions, base_data_factory, load=5):
    data = base_data_factory()
    data["DEFINITIONS"] = definitions
    data["ENERGY_NETWORK"] = {
        "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
        "UNITS": [
            {"NAME": "turbine", "TYPE": "GAS_TURBINE", "INPUT": "fuel", "MODEL": model},
            {"NAME": "load", "TYPE": "MECHANICAL_CONSUMER", "INPUT": "turbine", "LOAD": load},
        ],
    }
    return data


@pytest.fixture
def turbine_network_data_factory(
    yaml_asset_builder_factory, minimal_installation_yaml_factory, yaml_fuel_type_builder_factory
):
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


def _run_turbine(model):
    topology, factories, consumers, _ = model.get_energy_network()
    simulation = EnergyNetworkSimulation(topology=topology, energy_unit_factories=factories)
    (load,) = consumers
    (period,) = load.demand.expression.get_periods()
    (load_connection,) = topology.get_incoming_connections(load.get_id())
    factories_by_name = {factory.get_name(): factory for factory in factories}
    fuel_connection = topology.get_connection(factories_by_name["fuel"].get_id(), factories_by_name["turbine"].get_id())
    result = simulation.run({load_connection.id: load.get_demand(period)}, period=period)
    return result.get_energy()[fuel_connection.id].value, result.get_capacity_failures()


@pytest.mark.parametrize("source", ["inline", "file"])
def test_gas_turbine_fuel_follows_its_model(source, turbine_network_data_factory, yaml_model_factory):
    resources = {}
    curve = CURVE
    if source == "file":
        curve = {"FILE": "curve.csv"}
        resources["curve.csv"] = MemoryResource(data=[[2, 4, 8], [0.1, 0.2, 0.3]], headers=["LOAD", "EFFICIENCY"])
    turbine = {"LOWER_HEATING_VALUE": TURBINE_LHV, "CURVE": curve}
    data = _turbine_model_data(turbine, {}, turbine_network_data_factory)

    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="turbine_model"), resources=resources
    )

    fuel, _ = _run_turbine(model)
    assert fuel == pytest.approx(EXPECTED_FUEL)


@pytest.mark.parametrize(("load", "exceeds_curve"), [(6, False), (10, True)])
def test_gas_turbine_curve_limit_reaches_the_simulation(
    load, exceeds_curve, turbine_network_data_factory, yaml_model_factory
):
    turbine = {"LOWER_HEATING_VALUE": TURBINE_LHV, "CURVE": CURVE}
    data = _turbine_model_data(turbine, {}, turbine_network_data_factory, load=load)
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="turbine_model"), resources={}
    )

    fuel, capacity_failures = _run_turbine(model)

    # Max power is the last curve load, 8 MW
    efficiency = 0.2 + 0.1 * (min(load, 8) - 4) / 4
    assert fuel == pytest.approx(load * 86400 / TURBINE_LHV / efficiency)
    assert bool(capacity_failures) is exceeds_curve


@pytest.mark.parametrize("file_key", ["FILE", "file"])
def test_turbine_file_is_listed_as_facility_resource(
    file_key, turbine_network_data_factory, configuration_service_factory
):
    turbine = {"LOWER_HEATING_VALUE": TURBINE_LHV, "CURVE": {file_key: "curve.csv"}}
    data = _turbine_model_data(turbine, {}, turbine_network_data_factory)

    configuration = configuration_service_factory(
        ResourceStream(stream=StringIO(yaml.dump(data)), name="turbine_model")
    ).get_configuration()

    assert "curve.csv" in configuration.facility_resource_names


@pytest.mark.parametrize(
    ("resources", "message"),
    [
        ({"curve.csv": MemoryResource(data=[[2, 4, 8], [0.1, 0.2, 0.3]], headers=["LOAD", "EFF"])}, "EFFICIENCY"),
        (
            {"curve.csv": MemoryResource(data=[[2, 4, "x"], [0.1, 0.2, 0.3]], headers=["LOAD", "EFFICIENCY"])},
            "non-numeric",
        ),
        (
            {"curve.csv": MemoryResource(data=[[8, 4, 0], [0.3, 0.2, 0]], headers=["LOAD", "EFFICIENCY"])},
            "FILE 'curve.csv'.*strictly increasing",
        ),
    ],
)
def test_gas_turbine_file_errors_are_reported(resources, message, turbine_network_data_factory, yaml_model_factory):
    turbine = {"LOWER_HEATING_VALUE": TURBINE_LHV, "CURVE": {"FILE": "curve.csv"}}
    data = _turbine_model_data(turbine, {}, turbine_network_data_factory)
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="turbine_model"), resources=resources
    )

    with pytest.raises(ModelValidationException, match=message):
        model.get_energy_network()


def test_invalid_inline_turbine_model_is_reported_at_the_model(turbine_network_data_factory, yaml_model_factory):
    turbine = {"LOWER_HEATING_VALUE": TURBINE_LHV, "CURVE": {"LOAD": [2, 4, 8], "EFFICIENCY": [0.1, 0.2, 1.5]}}
    data = _turbine_model_data(turbine, {}, turbine_network_data_factory)
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="turbine_model"), resources={}
    )

    with pytest.raises(ModelValidationException) as exc_info:
        model.get_energy_network()

    (error,) = exc_info.value.errors()
    assert error.location.keys[:5] == ["ENERGY_NETWORK", "UNITS", 0, "GAS_TURBINE", "MODEL"]
    assert "Got 1.5 at load 8" in error.message


@pytest.mark.parametrize("headers", [["load", "efficiency"], ["Load", "EFFICIENCY"]])
def test_turbine_file_headers_are_case_insensitive(headers, turbine_network_data_factory, yaml_model_factory):
    turbine = {"LOWER_HEATING_VALUE": TURBINE_LHV, "CURVE": {"FILE": "curve.csv"}}
    data = _turbine_model_data(turbine, {}, turbine_network_data_factory)
    resources = {"curve.csv": MemoryResource(data=[[2, 4, 8], [0.1, 0.2, 0.3]], headers=headers)}
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="turbine_model"), resources=resources
    )

    fuel, _ = _run_turbine(model)

    assert fuel == pytest.approx(EXPECTED_FUEL)


def test_turbine_model_resolved_from_definitions_still_validates_file_existence(
    turbine_network_data_factory, yaml_model_factory
):
    turbine = {"LOWER_HEATING_VALUE": TURBINE_LHV, "CURVE": {"FILE": "missing.csv"}}
    data = _turbine_model_data("my_turbine", {"TURBINES": {"my_turbine": turbine}}, turbine_network_data_factory)
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="turbine_model"), resources={}
    )

    with pytest.raises(ModelValidationException, match="resource not found"):
        model.get_energy_network()


def test_invalid_inline_turbine_file_is_still_validated_for_existence(turbine_network_data_factory, yaml_model_factory):
    turbine = {"LOWER_HEATING_VALUE": TURBINE_LHV, "CURVE": {"FILE": "missing.csv"}}
    data = _turbine_model_data(turbine, {}, turbine_network_data_factory)
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="turbine_model"), resources={}
    )

    with pytest.raises(ModelValidationException, match="resource not found"):
        model.get_energy_network()


def test_gas_turbine_model_is_resolved_from_definitions(turbine_network_data_factory, yaml_model_factory):
    turbine = {"LOWER_HEATING_VALUE": TURBINE_LHV, "CURVE": CURVE}
    data = _turbine_model_data("my_turbine", {"TURBINES": {"my_turbine": turbine}}, turbine_network_data_factory)
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="turbine_model"), resources={}
    )

    fuel, _ = _run_turbine(model)

    assert fuel == pytest.approx(EXPECTED_FUEL)


def test_turbine_definition_reference_not_found_is_reported(turbine_network_data_factory, yaml_model_factory):
    data = _turbine_model_data("missing_turbine", {}, turbine_network_data_factory)
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="turbine_model"), resources={}
    )

    with pytest.raises(ModelValidationException, match="missing_turbine.*not found. Available definitions"):
        model.get_energy_network()


GENERATOR_MODEL = {"CURVE": {"POWER": [5, 10], "FUEL": [20000, 35000]}}
# 7 MW sits between the points: fuel is interpolated linearly, so fuel = 20000 + (35000 - 20000) * (7 - 5) / (10 - 5)
EXPECTED_GENERATOR_FUEL = 20000 + (35000 - 20000) * (7 - 5) / (10 - 5)


def _generator_model_data(model, definitions, base_data_factory, load=7):
    data = base_data_factory()
    data["DEFINITIONS"] = definitions
    data["ENERGY_NETWORK"] = {
        "SOURCES": [{"NAME": "fuel", "TYPE": "FUEL_GAS_SOURCE"}],
        "UNITS": [
            {"NAME": "genset", "TYPE": "GENERATOR", "INPUT": "fuel", "MODEL": model},
            {"NAME": "load", "TYPE": "ELECTRICAL_CONSUMER", "INPUT": "genset", "LOAD": load},
        ],
    }
    return data


def _run_generator(model):
    topology, factories, consumers, _ = model.get_energy_network()
    simulation = EnergyNetworkSimulation(topology=topology, energy_unit_factories=factories)
    (load,) = consumers
    (period,) = load.demand.expression.get_periods()
    (load_connection,) = topology.get_incoming_connections(load.get_id())
    factories_by_name = {factory.get_name(): factory for factory in factories}
    fuel_connection = topology.get_connection(factories_by_name["fuel"].get_id(), factories_by_name["genset"].get_id())
    result = simulation.run({load_connection.id: load.get_demand(period)}, period=period)
    return result.get_energy()[fuel_connection.id].value, result.get_capacity_failures()


def test_generator_fuel_follows_its_model(turbine_network_data_factory, yaml_model_factory):
    data = _generator_model_data(GENERATOR_MODEL, {}, turbine_network_data_factory)
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="generator_model"), resources={}
    )

    fuel, _ = _run_generator(model)
    assert fuel == pytest.approx(EXPECTED_GENERATOR_FUEL)


def test_generator_model_is_resolved_from_definitions(turbine_network_data_factory, yaml_model_factory):
    data = _generator_model_data(
        "my_generator", {"GENERATORS": {"my_generator": GENERATOR_MODEL}}, turbine_network_data_factory
    )
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="generator_model"), resources={}
    )

    fuel, _ = _run_generator(model)
    assert fuel == pytest.approx(EXPECTED_GENERATOR_FUEL)


def test_generator_definition_reference_not_found_is_reported(turbine_network_data_factory, yaml_model_factory):
    data = _generator_model_data("missing_generator", {}, turbine_network_data_factory)
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="generator_model"), resources={}
    )

    with pytest.raises(ModelValidationException, match="missing_generator.*not found. Available definitions"):
        model.get_energy_network()


def test_invalid_inline_generator_model_is_reported_at_the_model(turbine_network_data_factory, yaml_model_factory):
    bad_model = {"CURVE": {"POWER": [5, 10], "FUEL": [20000, -5]}}  # fuel must not be negative
    data = _generator_model_data(bad_model, {}, turbine_network_data_factory)
    model = yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="generator_model"), resources={}
    )

    with pytest.raises(ModelValidationException) as exc_info:
        model.get_energy_network()

    (error,) = exc_info.value.errors()
    assert error.location.keys[:5] == ["ENERGY_NETWORK", "UNITS", 0, "GENERATOR", "MODEL"]
    assert "must not be negative" in error.message


def _tabular_model(
    yaml_asset_builder_factory,
    minimal_installation_yaml_factory,
    yaml_fuel_type_builder_factory,
    yaml_model_factory,
    table_rows,
):
    asset = (
        yaml_asset_builder_factory()
        .with_test_data()
        .with_fuel_types([yaml_fuel_type_builder_factory().with_test_data().with_name("fuel").validate()])
        .with_installations([minimal_installation_yaml_factory(fuel_name="fuel")])
        .with_time_series([YamlTimeSeriesBuilder().with_name("SIM1").with_type("DEFAULT").with_file("SIM1").validate()])
        .with_start("2020-01-01")
        .with_end("2022-01-01")
        .validate()
    )
    data = asset.model_dump(by_alias=True, exclude_unset=True, mode="json")
    data["ENERGY_NETWORK"] = {
        "SOURCES": [{"NAME": "fuel_source", "TYPE": "FUEL_GAS_SOURCE"}],
        "UNITS": [
            {
                "NAME": "pump",
                "TYPE": "TABULAR_CONSUMER",
                "INPUT": "fuel_source",
                "FILE": "table.csv",
                "VARIABLES": {"RATE": "SIM1;RATE"},
            }
        ],
    }
    return yaml_model_factory(
        configuration=ResourceStream(stream=StringIO(yaml.dump(data)), name="energy_network_model"),
        resources={
            "SIM1": MemoryResource(data=[["2020-01-01", "2021-01-01"], [1.5, 2.5]], headers=["DATE", "RATE"]),
            "table.csv": MemoryResource(data=table_rows, headers=["RATE", "FUEL"]),
        },
    )


def test_tabular_consumer_reads_its_file_and_time_series_variables(
    yaml_asset_builder_factory,
    minimal_installation_yaml_factory,
    yaml_fuel_type_builder_factory,
    yaml_model_factory,
):
    model = _tabular_model(
        yaml_asset_builder_factory,
        minimal_installation_yaml_factory,
        yaml_fuel_type_builder_factory,
        yaml_model_factory,
        table_rows=[[1.0, 2.0, 3.0], [10.0, 20.0, 30.0]],
    )

    _topology, _factories, (pump,), _periods = model.get_energy_network()

    demands = [pump.get_demand(period).value for period in pump.demand.variables["RATE"].get_periods()]
    assert demands == pytest.approx([15, 25])


def test_invalid_tabular_file_is_reported_at_the_energy_network(
    yaml_asset_builder_factory,
    minimal_installation_yaml_factory,
    yaml_fuel_type_builder_factory,
    yaml_model_factory,
):
    model = _tabular_model(
        yaml_asset_builder_factory,
        minimal_installation_yaml_factory,
        yaml_fuel_type_builder_factory,
        yaml_model_factory,
        table_rows=[[1.0], [10.0]],
    )

    with pytest.raises(ModelValidationException) as error:
        model.get_energy_network()

    assert any("ENERGY_NETWORK" in str(e.location) for e in error.value.errors())
