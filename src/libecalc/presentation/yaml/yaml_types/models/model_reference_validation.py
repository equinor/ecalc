from typing import Annotated, Any

from pydantic import AfterValidator
from pydantic_core import PydanticCustomError
from pydantic_core.core_schema import ValidationInfo

from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlFacilityModelType,
)
from libecalc.presentation.yaml.yaml_types.models.model_reference import ModelName
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType
from libecalc.presentation.yaml.yaml_validation_context import (
    ModelContext,
    YamlModelValidationContextNames,
)


class InvalidModelReferenceError(ValueError):
    def __init__(self, model_reference: ModelName):
        self.model_reference = model_reference


class ModelReferenceNotFound(InvalidModelReferenceError):
    pass


class InvalidModelReferenceType(InvalidModelReferenceError):
    def __init__(self, model_reference: ModelName, model: ModelContext):
        self.model = model
        super().__init__(model_reference=model_reference)


def check_model_reference(
    model_reference: Any,
    available_models: dict["ModelName", ModelContext],
    allowed_types: list[str],
) -> str:
    if model_reference not in available_models:
        raise ModelReferenceNotFound(model_reference=model_reference)

    model = available_models[model_reference]

    if model.type not in allowed_types:
        raise InvalidModelReferenceType(model_reference=model_reference, model=model)

    return model_reference


def check_field_model_reference(allowed_types: list[str]):
    allowed_model_types = [
        allowed_type for allowed_type in allowed_types if allowed_type != YamlModelType.COMPRESSOR_WITH_TURBINE
    ]

    def check_model_reference_wrapper(model_reference: Any, info: ValidationInfo):
        if not info.context:
            return model_reference

        assert YamlModelValidationContextNames.model_types in info.context

        models_context = info.context.get(YamlModelValidationContextNames.model_types)
        try:
            try:
                model_reference = check_model_reference(
                    model_reference,
                    available_models=models_context,
                    allowed_types=allowed_types,
                )

            except InvalidModelReferenceType as e:
                raise PydanticCustomError(
                    "model_reference_type_invalid",
                    "Model '{model_reference}' with type {model_type} is not allowed",
                    {
                        "model_reference": e.model_reference,
                        "model_type": e.model.type,
                    },
                ) from e

            model = models_context[model_reference]

            # Also check compressor models in turbine
            if model.type == YamlModelType.COMPRESSOR_WITH_TURBINE:
                # Handle the compressor_model in turbine, it should be limited to the specified types.
                try:
                    check_model_reference(
                        model.compressor_model,
                        allowed_types=allowed_model_types,
                        available_models=models_context,
                    )

                except InvalidModelReferenceType as e:
                    raise PydanticCustomError(
                        "model_reference_type_invalid",
                        "Turbine '{turbine_reference}' with compressor model '{model_reference}' of type {model_type} is not allowed",
                        {
                            "turbine_reference": model_reference,
                            "model_reference": e.model_reference,
                            "model_type": e.model.type,
                        },
                    ) from e

        except ModelReferenceNotFound as e:
            raise PydanticCustomError(
                "model_reference_not_found",
                "Model '{model_reference}' not found",
                {
                    "model_reference": e.model_reference,
                },
            ) from e

    return check_model_reference_wrapper


GeneratorSetModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            allowed_types=[
                YamlFacilityModelType.ELECTRICITY2FUEL,
            ]
        )
    ),
]

CompressorEnergyUsageModelModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            allowed_types=[
                YamlFacilityModelType.TABULAR,
                YamlFacilityModelType.COMPRESSOR_TABULAR,
                YamlModelType.COMPRESSOR_WITH_TURBINE,
                YamlModelType.SINGLE_SPEED_COMPRESSOR_TRAIN,
                YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN,
                YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN,
            ]
        )
    ),
]

MultipleStreamsEnergyUsageModelModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            allowed_types=[
                YamlModelType.COMPRESSOR_WITH_TURBINE,
                YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES,
            ]
        )
    ),
]

PumpEnergyUsageModelModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            allowed_types=[
                YamlFacilityModelType.TABULAR,
                YamlFacilityModelType.PUMP_CHART_SINGLE_SPEED,
                YamlFacilityModelType.PUMP_CHART_VARIABLE_SPEED,
            ]
        )
    ),
]

TabulatedEnergyUsageModelModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            allowed_types=[
                YamlFacilityModelType.TABULAR,
            ]
        )
    ),
]

CompressorStageModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            allowed_types=[
                YamlModelType.COMPRESSOR_CHART,
                YamlFacilityModelType.COMPRESSOR_TABULAR,
                YamlFacilityModelType.TABULAR,
            ]
        )
    ),
]

FluidModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            allowed_types=[
                YamlModelType.FLUID,
            ]
        )
    ),
]

TurbineModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            allowed_types=[
                YamlModelType.TURBINE,
            ]
        )
    ),
]
