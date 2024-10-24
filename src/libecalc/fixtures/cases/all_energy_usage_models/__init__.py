from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader

"""
Test project for All Energy Usage Models

The purpose of this fixture is to try to cover as many different energy usage models as possible from yaml to result.

"""


@pytest.fixture
def all_energy_usage_models_yaml() -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent / "data",
        main_file="all_energy_usage_models.yaml",
        resource_names=[
            "einput/predefined_compressor_chart_curves.csv",
            "einput/genset.csv",
            "einput/pump_tabular.csv",
            "einput/pumpchart.csv",
            "einput/pumpchart_variable_speed.csv",
            "einput/compressor_sampled_1d.csv",
            "einput/tabular.csv",
            "sim/base_profile.csv",
            "sim/flare.csv",
        ],
    )
