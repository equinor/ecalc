import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset

MINIMAL_ASSET_DATA = {
    "FUEL_TYPES": [],
    "INSTALLATIONS": [],
    "END": "2020-01-01",
}

ECALC_EVENTS_DATA = [
    {
        "TYPE": "OTHER",
        "START": "2020-01-01",
        "NAME": "event",
    }
]


class TestYamlAssetVersion:
    def test_v2_only_field_in_v1_fails(self):
        with pytest.raises(EcalcValidationException) as exc_info:
            YamlAsset.model_validate(
                {
                    **MINIMAL_ASSET_DATA,
                    "VERSION": "1",
                    "ECALC_EVENTS": ECALC_EVENTS_DATA,
                }
            )

        assert "ECALC_EVENTS" in str(exc_info.value)
        assert "VERSION 2 or higher" in str(exc_info.value)

    def test_v2_only_field_in_v2_is_ok(self):
        asset = YamlAsset.model_validate(
            {
                **MINIMAL_ASSET_DATA,
                "VERSION": "2",
                "ECALC_EVENTS": ECALC_EVENTS_DATA,
            }
        )

        assert asset.version.major == 2
        assert len(asset.ecalc_events) == 1

    def test_v1_only_fields_in_v1_is_ok(self):
        asset = YamlAsset.model_validate(
            {
                **MINIMAL_ASSET_DATA,
                "VERSION": "1",
            }
        )

        assert asset.version.major == 1

    def test_v1_only_fields_in_v2_is_ok(self):
        asset = YamlAsset.model_validate(
            {
                **MINIMAL_ASSET_DATA,
                "VERSION": "2",
            }
        )

        assert asset.version.major == 2

    def test_v2_only_field_with_unspecified_version_fails(self):
        # Will fallback to version 1 as default (for now), and therefore fail
        with pytest.raises(EcalcValidationException) as exc_info:
            YamlAsset.model_validate(
                {
                    **MINIMAL_ASSET_DATA,
                    "ECALC_EVENTS": ECALC_EVENTS_DATA,
                }
            )

        assert "ECALC_EVENTS" in str(exc_info.value)
        assert "VERSION 2 or higher" in str(exc_info.value)

    def test_v1_only_fields_with_unspecified_version_is_ok(self):
        asset = YamlAsset.model_validate(MINIMAL_ASSET_DATA)

        assert asset.version.major == 1
