from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader

NEXTGEN_RESOURCE_NAMES = [
    "compressor_chart.csv",
    "base_profile.csv",
    "sampled_el_compressor.csv",
    "sampled_fuel_compressor.csv",
    "sampled_fuel_turbine.csv",
    "sampled_mech_compressor.csv",
]


@pytest.fixture
def nextgen_yaml() -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent,
        main_file="model.yaml",
        resource_names=NEXTGEN_RESOURCE_NAMES,
    )
