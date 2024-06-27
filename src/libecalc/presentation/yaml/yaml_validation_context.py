from typing import Dict, List, Protocol, TypedDict, Union

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


YamlModelValidationContext = TypedDict(
    "YamlModelValidationContext",
    {
        YamlModelValidationContextNames.resource_file_names: List[str],  # type: ignore
        YamlModelValidationContextNames.expression_tokens: List[str],
        YamlModelValidationContextNames.model_types: Dict[ModelName, ModelContext],
    },
    total=True,
)
