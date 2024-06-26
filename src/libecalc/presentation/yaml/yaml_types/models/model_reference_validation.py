from typing import TYPE_CHECKING, Any, Dict, List, Union

from pydantic_core import PydanticCustomError
from pydantic_core.core_schema import ValidationInfo

from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType
from libecalc.presentation.yaml.yaml_validation_context import (
    YamlModelValidationContextNames,
)

if TYPE_CHECKING:
    from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
        YamlFacilityModel,
    )
    from libecalc.presentation.yaml.yaml_types.models import YamlModel
    from libecalc.presentation.yaml.yaml_types.models.model_reference import ModelName

    ModelType = Union[YamlModel, YamlFacilityModel]


class InvalidModelReferenceError(ValueError):
    def __init__(self, model_reference: "ModelName"):
        self.model_reference = model_reference


class ModelReferenceNotFound(InvalidModelReferenceError):
    pass


class InvalidModelReferenceType(InvalidModelReferenceError):
    def __init__(self, model_reference: "ModelName", model: "ModelType"):
        self.model = model
        super().__init__(model_reference=model_reference)


def check_model_reference(
    model_reference: Any,
    available_models: Dict["ModelName", "ModelType"],
    allowed_types: List["ModelType"],
) -> str:
    if model_reference not in available_models:
        raise ModelReferenceNotFound(model_reference=model_reference)

    model = available_models[model_reference]

    if model.type not in allowed_types:
        raise InvalidModelReferenceType(model_reference=model_reference, model=model)

    return model_reference


def check_field_model_reference(allowed_types: List["ModelType"]):
    allowed_model_types = [
        allowed_type for allowed_type in allowed_types if allowed_type != YamlModelType.COMPRESSOR_WITH_TURBINE
    ]

    def check_model_reference_wrapper(model_reference: Any, info: ValidationInfo):
        if not info.context:
            return model_reference

        assert YamlModelValidationContextNames.model_types in info.context

        models_context = info.context.get(YamlModelValidationContextNames.model_types)
        try:
            model_reference = check_model_reference(
                model_reference,
                available_models=models_context,
                allowed_types=allowed_types,
            )
            model = models_context[model_reference]
            if model.type == YamlModelType.COMPRESSOR_WITH_TURBINE:
                # Handle the compressor_model in turbine, it should be limited to the specified types.
                check_model_reference(
                    model.compressor_model,
                    allowed_types=allowed_model_types,
                    available_models=models_context,
                )
        except ModelReferenceNotFound as e:
            raise PydanticCustomError(
                "model_reference_not_found",
                "Model '{model_reference}' not found",
                {
                    "model_reference": e.model_reference,
                },
            ) from e
        except InvalidModelReferenceType as e:
            raise PydanticCustomError(
                "model_reference_type_invalid",
                "Model '{model_reference}' with type {model_type} is not allowed",
                {
                    "model_reference": e.model_reference,
                    "model_type": e.model.type,
                },
            ) from e

    return check_model_reference_wrapper
