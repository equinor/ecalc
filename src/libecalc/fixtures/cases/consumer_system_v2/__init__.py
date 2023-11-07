from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader
from libecalc.fixtures.cases.consumer_system_v2.consumer_system_v2_dto import (
    consumer_system_v2_dto,
    consumer_system_v2_dto_fixture,
)

"""
Test project for Consumer System v2

The purpose of this fixture is to verify correctness of the new consumer system v2 and regression to the
old consumer system (v1)

"""


@pytest.fixture
def consumer_system_v2_yaml() -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent / "data",
        main_file="consumer_system_v2.yaml",
        resource_names=["compressor_sampled_1d.csv", "pumpchart.csv", "genset.csv", "compressor1.csv"],
    )
