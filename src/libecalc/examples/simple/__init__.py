from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader

"""
Test project for Simple

The purpose of this fixture is to show a simple example of an eCalc model for testing and examples, and to
have a lightweight version of a complete model for lightweight e2e testing.

"""


@pytest.fixture
def simple_yaml() -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent,
        main_file="model.yaml",
        resource_names=[
            "compressor_sampled.csv",
            "compressor_sampled_with_turbine.csv",
            "genset.csv",
            "production_data.csv",
            "pump_chart.csv",
            "pump_sampled.csv",
        ],
    )


@pytest.fixture
def simple_temporal_yaml() -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent,
        main_file="model_temporal.yaml",
        resource_names=[
            "compressor_sampled.csv",
            "compressor_sampled_with_turbine.csv",
            "genset.csv",
            "production_data.csv",
            "pump_chart.csv",
            "pump_sampled.csv",
        ],
    )
