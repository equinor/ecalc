from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader

"""
Test project for Drogon (synthetic test case used for various purposes outside this project)

The purpose of this fixture is to showcase the synthetic model Drogon in an eCalc Model for use with
examples and testing.

"""


@pytest.fixture
def drogon_yaml() -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent,
        main_file="model.yaml",
        resource_names=[
            "drogon_mean.csv",
            "genset.csv",
            "wi_200bar_ssp.csv",
        ],
    )
