import json
from pathlib import Path
from typing import Dict

import pytest
from libecalc.common.math.numbers import Numbers
from libecalc.examples import advanced, simple
from libecalc.fixtures import YamlCase
from libecalc.fixtures.cases import (
    all_energy_usage_models,
    consumer_system_v2,
    ltp_export,
)


def _round_floats(obj):
    if isinstance(obj, float):
        return float(Numbers.format_to_precision(obj, precision=8))
    elif isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_round_floats(v) for v in obj]
    return obj


@pytest.fixture
def rounded_snapshot(snapshot):
    def rounded_snapshot(data: Dict, snapshot_name: str):
        snapshot.assert_match(
            json.dumps(_round_floats(data), sort_keys=True, indent=4, default=str), snapshot_name=snapshot_name
        )

    return rounded_snapshot


valid_example_cases = {
    "simple": (Path(simple.__file__).parent / "model.yaml").absolute(),
    "simple_temporal": (Path(simple.__file__).parent / "model_temporal.yaml").absolute(),
    "advanced": (Path(advanced.__file__).parent / "model.yaml").absolute(),
    "advanced_docs": (Path("../../../docs/docs/about/modelling/examples/advanced/model.yaml")).absolute(),
    "ltp": (Path(ltp_export.__file__).parent / "data" / "ltp_export.yaml").absolute(),
    "all_energy_usage_models": (
        Path(all_energy_usage_models.__file__).parent / "data" / "all_energy_usage_models.yaml"
    ).absolute(),
    "consumer_system_v2": (Path(consumer_system_v2.__file__).parent / "data" / "consumer_system_v2.yaml").absolute(),
}


# The value should be the name of a fixture returning the YamlCase for the example
valid_example_yaml_case_fixture_names = {
    "simple": "simple_yaml",
    "simple_temporal": "simple_temporal_yaml",
    "advanced": "advanced_yaml",
    "advanced_docs": "advanced_docs_yaml",
    "ltp": "ltp_export_yaml",
    "all_energy_usage_models": "all_energy_usage_models_yaml",
    "consumer_system_v2": "consumer_system_v2_yaml",
}

invalid_example_cases = {
    "simple_duplicate_names": (Path(simple.__file__).parent / "model_duplicate_names.yaml").absolute(),
    "simple_multiple_energy_models_one_consumer": (
        Path(simple.__file__).parent / "model_multiple_energy_models_one_consumer.yaml"
    ).absolute(),
    "simple_duplicate_emissions_in_fuel": (
        Path(simple.__file__).parent / "model_duplicate_emissions_in_fuel.yaml"
    ).absolute(),
}


@pytest.fixture(scope="session")
def simple_yaml_path():
    return valid_example_cases["simple"]


@pytest.fixture(scope="session")
def simple_temporal_yaml_path():
    return valid_example_cases["simple_temporal"]


@pytest.fixture(scope="session")
def simple_duplicate_names_yaml_path():
    return invalid_example_cases["simple_duplicate_names"]


@pytest.fixture(scope="session")
def simple_multiple_energy_models_yaml_path():
    return invalid_example_cases["simple_multiple_energy_models_one_consumer"]


@pytest.fixture(scope="session")
def simple_duplicate_emissions_yaml_path():
    return invalid_example_cases["simple_duplicate_emissions_in_fuel"]


@pytest.fixture(scope="session")
def advanced_yaml_path():
    return valid_example_cases["advanced"]


@pytest.fixture(scope="session")
def advanced_docs_yaml_path():
    return valid_example_cases["advanced_docs"]


@pytest.fixture
def ltp_yaml_path():
    return valid_example_cases["ltp"]


@pytest.fixture(
    scope="function", params=list(valid_example_yaml_case_fixture_names.items()), ids=lambda param: param[0]
)
def valid_example_case_yaml_case(request) -> YamlCase:
    """
    Parametrized fixture returning each YamlCase for all valid examples
    """
    yaml_case = request.getfixturevalue(request.param[1])
    return yaml_case
