from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader

"""
Test project for LTP Export

The purpose of this fixture is to try to cover as much as possible of the Category and LTP/STP Export functionality
wrt using it in LTP Export tests to test both correctness and regression.

"""


@pytest.fixture
def ltp_export_yaml() -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent / "data",
        main_file="ltp_export.yaml",
        resource_names=[
            "sim/prod_inj_forecast.csv",
            "sim/steamgen.csv",
            "sim/flare_diesel_cold_venting_fugitives.csv",
            "sim/mobile_installations_host_field.csv",
            "sim/mobile_installations_satellite_A.csv",
            "sim/mobile_installations_satellite_B.csv",
            "einput/genset_17MW.csv",
            "einput/onshore_power.csv",
            "einput/pumpchart_water_inj.csv",
            "einput/gascompression.csv",
            "einput/gascompression_zero_power.csv",
        ],
    )
