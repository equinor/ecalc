from typing import Any

from pydantic import TypeAdapter, ValidationError

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_model import YamlNextgenModel
from libecalc.presentation.yaml.yaml_types.yaml_version import DEFAULT_YAML_VERSION, V1, YamlMajorVersion

YAML_VERSION_KEY = "YAML_VERSION"

YamlDocument = YamlAsset | YamlNextgenModel


def is_legacy_yaml(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    try:
        major_version = TypeAdapter(YamlMajorVersion).validate_python(data.get(YAML_VERSION_KEY, DEFAULT_YAML_VERSION))
    except ValidationError:
        return False
    return major_version == V1.major


def validate_yaml_document(data: Any, context: dict[str, Any] | None = None) -> YamlDocument:
    model = YamlAsset if is_legacy_yaml(data) else YamlNextgenModel
    return model.model_validate(data, context=context)
