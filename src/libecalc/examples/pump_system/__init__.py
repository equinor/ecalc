from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader

"""
Test project for Pump System (synthetic test case used for various purposes outside this project)

The purpose of this fixture is to showcase a synthetic pump system model in an eCalc Model for use with
examples and testing.
"""


@pytest.fixture
def pump_system_yaml() -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent,
        main_file="model.yaml",
        resource_names=[
            "base_profile.csv",
            "genset.csv",
            "pump_chart.csv",
        ],
    )
