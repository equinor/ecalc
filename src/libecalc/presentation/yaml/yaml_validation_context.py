from typing import List, TypedDict


class YamlModelValidationContextNames:
    resource_file_names = "resource_file_names"
    expression_tokens = "expression_tokens"


YamlModelValidationContext = TypedDict(
    "YamlModelValidationContext",
    {
        YamlModelValidationContextNames.resource_file_names: List[str],  # type: ignore
        YamlModelValidationContextNames.expression_tokens: List[str],
    },
    total=True,
)
