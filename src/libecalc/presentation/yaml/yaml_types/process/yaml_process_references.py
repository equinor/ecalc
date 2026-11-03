"""
Shared reference type aliases for YAML process types.
"""

from typing import Any

from pydantic import BeforeValidator, ValidationInfo

from libecalc.presentation.yaml.yaml_types import YamlBase

type InstanceReference = str
type DefinitionReference = str


def validate_definition_reference_or_inline_model[Model: YamlBase](model_cls: type[Model]):
    def validate(v: Any, info: ValidationInfo) -> str | Model:
        return v if isinstance(v, str) else model_cls.model_validate(v, context=info.context)

    return BeforeValidator(validate)
