from typing import Protocol, TypedDict, Union

ModelName = str


class Model(Protocol):
    type: str


class CompressorWithTurbineModel(Model, Protocol):
    compressor_model: ModelName


ModelContext = Union[Model, CompressorWithTurbineModel]


class YamlModelValidationContextNames:
    resource_file_names = "resource_file_names"
    expression_tokens = "expression_tokens"
    model_types = "model_types"
    model_name = "model_name"


YamlModelValidationContext = TypedDict(
    "YamlModelValidationContext",
    {
        YamlModelValidationContextNames.resource_file_names: list[str],  # type: ignore
        YamlModelValidationContextNames.expression_tokens: list[str],
        YamlModelValidationContextNames.model_types: dict[ModelName, ModelContext],
        YamlModelValidationContextNames.model_name: str,
    },
    total=True,
)
