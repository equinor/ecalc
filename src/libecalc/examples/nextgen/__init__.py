from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader
from libecalc.presentation.yaml.yaml_types.yaml_version import LATEST_YAML_VERSION

NEXTGEN_RESOURCE_NAMES = [
    "compressor_chart.csv",
    "base_profile.csv",
    "sampled_el_compressor.csv",
    "sampled_fuel_compressor.csv",
    "sampled_fuel_turbine.csv",
    "sampled_mech_compressor.csv",
]


def load_nextgen_yaml(yaml_version: int) -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent / f"v{yaml_version}",
        main_file="model.yaml",
        resource_names=NEXTGEN_RESOURCE_NAMES,
    )


@pytest.fixture
def nextgen_yaml() -> YamlCase:
    return load_nextgen_yaml(LATEST_YAML_VERSION)
