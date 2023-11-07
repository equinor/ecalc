from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader

"""
Test project for Advanced

The purpose of this fixture is to showcase an advanced version an eCalc Model for use with
examples and testing.

"""


@pytest.fixture
def advanced_yaml() -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent,
        main_file="model.yaml",
        resource_names=[
            "base_profile.csv",
            "compressor_chart.csv",
            "compressor_sampled.csv",
            "genset.csv",
            "pump_chart.csv",
        ],
    )
