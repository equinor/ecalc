from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase, YamlCaseLoader


@pytest.fixture
def compressor_systems_and_compressor_train_temporal() -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent / "data",
        main_file="root_model.yaml",
        resource_names=[
            "predefined_compressor_chart_curves.csv",
            "genset.csv",
            "compressor_sampled_1d.csv",
            "base_profile.csv",
            "flare.csv",
        ],
    )
