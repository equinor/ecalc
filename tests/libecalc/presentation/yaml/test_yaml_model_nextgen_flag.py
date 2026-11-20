import pytest

from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.testing.yaml_builder import YamlLegacyAssetBuilder


@pytest.fixture
def legacy_configuration(yaml_asset_configuration_service_factory):
    asset = YamlLegacyAssetBuilder().with_test_data().validate()
    return yaml_asset_configuration_service_factory(asset, "legacy").get_configuration()


def _messages(error: ModelValidationException) -> str:
    return " ".join(e.message for e in error.errors())


def test_legacy_model_is_rejected_when_nextgen(legacy_configuration, yaml_model_factory):
    model = yaml_model_factory(legacy_configuration, {}, nextgen=True)

    with pytest.raises(ModelValidationException) as exc_info:
        model.validate_for_run()

    assert "not available in a NextGen model" in _messages(exc_info.value)


def test_legacy_model_is_accepted_when_not_nextgen(legacy_configuration, yaml_model_factory):
    model = yaml_model_factory(legacy_configuration, {}, nextgen=False)

    model.validate_for_run()


def test_validate_nextgen_rejects_legacy_model_when_nextgen(legacy_configuration, yaml_model_factory):
    model = yaml_model_factory(legacy_configuration, {}, nextgen=True)

    with pytest.raises(ModelValidationException) as exc_info:
        model.validate_nextgen()

    assert "not available in a NextGen model" in _messages(exc_info.value)
