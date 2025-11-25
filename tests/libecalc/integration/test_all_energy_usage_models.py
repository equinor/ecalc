import pytest

from libecalc.fixtures import YamlCase
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.yaml.model import YamlModel


@pytest.fixture
def yaml_model(all_energy_usage_models_yaml: YamlCase) -> YamlModel:
    model = all_energy_usage_models_yaml.get_yaml_model()
    model.validate_for_run()
    model.evaluate_energy_usage()
    model.evaluate_emissions()
    return model


@pytest.mark.snapshot
def test_all_results(yaml_model, rounded_snapshot):
    snapshot_name = "all_energy_usage_models_v3.json"

    asset_result = get_asset_result(yaml_model).model_dump()
    rounded_snapshot(data=asset_result, snapshot_name=snapshot_name)
