from io import StringIO

import pytest
import yaml

from libecalc.presentation.yaml.domain.energy import TimeSeriesJunctionFactory
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.testing.yaml_builder import YamlTimeSeriesBuilder


def test_returns_nothing_without_an_energy_network(minimal_model_yaml_factory, yaml_model_factory):
    model = yaml_model_factory(configuration=minimal_model_yaml_factory().get_configuration(), resources={})

    assert model.get_energy_network() == (None, (), (), [])


@pytest.mark.parametrize(("period_index", "grid_share"), [(0, 6), (1, 8)])
def test_input_capacity_reads_a_time_series_referenced_only_by_the_junction(
    yaml_asset_builder_factory,
    minimal_installation_yaml_factory,
    yaml_fuel_type_builder_factory,
    yaml_model_factory,
    period_index,
    grid_share,
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

    topology, energy_unit_factories, _consumers, _periods = model.get_energy_network()

    assert topology is not None
    factories_by_name = {factory.get_name(): factory for factory in energy_unit_factories}
    bus = factories_by_name["bus"]
    assert isinstance(bus, TimeSeriesJunctionFactory)
    grid_limit = bus.input_capacities[factories_by_name["grid"].get_id()]

    assert grid_limit.get_value(grid_limit.get_periods()[period_index]) == pytest.approx(grid_share)
