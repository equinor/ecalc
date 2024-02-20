from typing import List, TypedDict


class YamlModelValidationContextNames:
    resource_file_names = "resource_file_names"


YamlModelValidationContext = TypedDict(
    "YamlModelValidationContext",
    {
        YamlModelValidationContextNames.resource_file_names: List[str],  # type: ignore
    },
    total=True,
)
