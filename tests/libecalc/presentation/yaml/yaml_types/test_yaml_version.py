import pytest
from pydantic import BaseModel, Field, ValidationError

from libecalc.common.version import Version
from libecalc.presentation.yaml.yaml_types.yaml_version import (
    AVAILABLE_SINCE_KEY,
    DEFAULT_YAML_VERSION,
    DEPRECATED_SINCE_KEY,
    REMOVED_SINCE_KEY,
    V1,
    V2,
    YamlElementLifecycle,
    YamlMajorVersion,
    _parse_major_version,
    get_root_field_names,
    get_unavailable_field_names,
    get_yaml_element_lifecycle,
    is_available_for_version,
    yaml_element_lifecycle,
)
from libecalc.version import current_yaml_version

V3 = Version(3, 0, 0)


def test_default_yaml_version_is_v1():
    assert DEFAULT_YAML_VERSION == V1.major == 1


class TestParseMajorVersion:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (1, 1),
            (2, 2),
            ("1", 1),
            ("2", 2),
            (" 2 ", 2),
        ],
    )
    def test_accepts_valid_values(self, value, expected):
        assert _parse_major_version(value) == expected

    def test_rejects_bool(self):
        with pytest.raises(ValueError, match="Invalid yaml version"):
            _parse_major_version(True)

    @pytest.mark.parametrize("value", [0, -1, current_yaml_version().major + 1])
    def test_rejects_out_of_range_values(self, value):
        with pytest.raises(ValueError, match="Invalid yaml version"):
            _parse_major_version(value)

    @pytest.mark.parametrize("value", ["2.0", "abc", "", "2x", 2.5])
    def test_rejects_invalid_formats(self, value):
        with pytest.raises(ValueError, match="Invalid yaml version"):
            _parse_major_version(value)


class TestYamlMajorVersionField:
    class _Holder(BaseModel):
        yaml_version: YamlMajorVersion

    def test_parses_int_and_string_values(self):
        assert self._Holder(yaml_version=2).yaml_version == 2
        assert self._Holder(yaml_version="2").yaml_version == 2

    def test_rejects_values_below_one(self):
        with pytest.raises(ValidationError):
            self._Holder(yaml_version=0)

    def test_rejects_values_above_current_yaml_version(self):
        with pytest.raises(ValidationError):
            self._Holder(yaml_version=current_yaml_version().major + 1)

    def test_json_schema_declares_min_and_max(self):
        schema = self._Holder.model_json_schema()
        yaml_version_schema = schema["properties"]["yaml_version"]
        assert yaml_version_schema["minimum"] == 1
        assert yaml_version_schema["maximum"] == current_yaml_version().major


class TestYamlElementLifecycleBuilder:
    def test_with_no_args_returns_empty_dict(self):
        assert yaml_element_lifecycle() == {}

    def test_includes_only_the_fields_that_are_set(self):
        assert yaml_element_lifecycle(available_since=V2) == {AVAILABLE_SINCE_KEY: "2.0.0"}
        assert yaml_element_lifecycle(deprecated_since=V2) == {DEPRECATED_SINCE_KEY: "2.0.0"}
        assert yaml_element_lifecycle(removed_since=V3) == {REMOVED_SINCE_KEY: "3.0.0"}

    def test_includes_all_fields_when_all_are_set(self):
        extra = yaml_element_lifecycle(available_since=V1, deprecated_since=V2, removed_since=V3)
        assert extra == {
            AVAILABLE_SINCE_KEY: "1.0.0",
            DEPRECATED_SINCE_KEY: "2.0.0",
            REMOVED_SINCE_KEY: "3.0.0",
        }


class TestGetYamlElementLifecycle:
    def test_defaults_to_available_since_v1_when_no_extra(self):
        field_info = Field()
        lifecycle = get_yaml_element_lifecycle(field_info)
        assert lifecycle == YamlElementLifecycle(available_since=V1, deprecated_since=None, removed_since=None)

    def test_parses_lifecycle_from_json_schema_extra(self):
        field_info = Field(json_schema_extra=yaml_element_lifecycle(available_since=V2, deprecated_since=V3))
        lifecycle = get_yaml_element_lifecycle(field_info)
        assert lifecycle.available_since == V2
        assert lifecycle.deprecated_since == V3
        assert lifecycle.removed_since is None

    def test_ignores_non_dict_json_schema_extra(self):
        field_info = Field(json_schema_extra=lambda schema: None)
        lifecycle = get_yaml_element_lifecycle(field_info)
        assert lifecycle == YamlElementLifecycle(available_since=V1, deprecated_since=None, removed_since=None)


class TestIsAvailableForVersion:
    @pytest.mark.parametrize(
        "lifecycle_kwargs, version, expected",
        [
            ({}, 1, True),
            ({}, 2, True),
            ({"available_since": V2}, 1, False),
            ({"available_since": V2}, 2, True),
            ({"deprecated_since": V2}, 2, True),
            ({"removed_since": V2}, 1, True),
            ({"removed_since": V2}, 2, False),
            ({"removed_since": V2}, 3, False),
            ({"available_since": V2, "removed_since": V3}, 1, False),
            ({"available_since": V2, "removed_since": V3}, 2, True),
            ({"available_since": V2, "removed_since": V3}, 3, False),
        ],
    )
    def test_is_available_for_version(self, lifecycle_kwargs, version, expected):
        field_info = Field(json_schema_extra=yaml_element_lifecycle(**lifecycle_kwargs))
        assert is_available_for_version(field_info, version) is expected


class _LifecycleModel(BaseModel):
    """Minimal model covering every lifecycle combination, for unit-testing the
    root-field-name helpers without depending on the full YamlAsset model."""

    legacy: str = Field(default="", json_schema_extra=yaml_element_lifecycle())
    introduced_in_v2: str = Field(default="", json_schema_extra=yaml_element_lifecycle(available_since=V2))
    deprecated_in_v2: str = Field(default="", json_schema_extra=yaml_element_lifecycle(deprecated_since=V2))
    removed_in_v2: str = Field(default="", json_schema_extra=yaml_element_lifecycle(removed_since=V2))
    no_lifecycle: str = ""


class TestGetRootFieldNames:
    def test_for_v1_excludes_only_fields_introduced_in_v2(self):
        # deprecated_in_v2 has no removed_since, so deprecation alone doesn't remove
        # availability; removed_in_v2 isn't removed until v2, so it's still available in v1.
        assert get_root_field_names(_LifecycleModel, 1) == {
            "legacy",
            "no_lifecycle",
            "deprecated_in_v2",
            "removed_in_v2",
        }

    def test_for_v2_includes_new_and_deprecated_but_not_removed_fields(self):
        assert get_root_field_names(_LifecycleModel, 2) == {
            "legacy",
            "no_lifecycle",
            "introduced_in_v2",
            "deprecated_in_v2",
        }


class TestGetUnavailableFieldNames:
    def test_for_v1_returns_fields_introduced_in_v2(self):
        unavailable = get_unavailable_field_names(_LifecycleModel, 1, _LifecycleModel.model_fields.keys())
        assert unavailable == {"introduced_in_v2"}

    def test_only_considers_the_given_field_names(self):
        unavailable = get_unavailable_field_names(
            _LifecycleModel, 1, {"introduced_in_v2", "legacy", "field_that_does_not_exist"}
        )
        assert unavailable == {"introduced_in_v2"}

    def test_for_v2_returns_fields_removed_at_v2(self):
        assert get_unavailable_field_names(_LifecycleModel, 2, _LifecycleModel.model_fields.keys()) == {"removed_in_v2"}
