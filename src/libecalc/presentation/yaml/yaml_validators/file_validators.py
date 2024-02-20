from pydantic_core import PydanticCustomError
from pydantic_core.core_schema import ValidationInfo

from libecalc.presentation.yaml.yaml_validation_context import (
    YamlModelValidationContextNames,
)


def file_exists_validator(value, info: ValidationInfo):
    if not info.context:
        return value

    assert YamlModelValidationContextNames.resource_file_names in info.context

    if value not in info.context[YamlModelValidationContextNames.resource_file_names]:
        raise PydanticCustomError(
            "resource_not_found",
            "resource not found, got '{resource_name}'",
            {"resource_name": value},
        )

    return value
