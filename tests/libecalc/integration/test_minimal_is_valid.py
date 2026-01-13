import pytest

from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.json_result.result import EcalcModelResult
from libecalc.presentation.yaml.model import YamlModel


@pytest.fixture
def minimal_asset_result(minimal_model_yaml_factory, resource_service_factory):
    minimal_configuration_service = minimal_model_yaml_factory()
    configuration = minimal_configuration_service.get_configuration()
    model = YamlModel(
        configuration=configuration,
        resource_service=resource_service_factory({}, configuration=configuration),
    )
    model.evaluate_energy_usage()
    return get_asset_result(model)


def test_is_valid_is_boolean(minimal_asset_result: EcalcModelResult):
    """
    We had a bug where all TimeSeriesBoolean values became floats because of rounding,
    this makes sure that does not happen again.
    """
    assert all(type(value) is bool for value in minimal_asset_result.component_result.is_valid.values)
