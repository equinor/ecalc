from typing import Any, Dict, List

from pydantic import AfterValidator
from pydantic_core import PydanticCustomError
from pydantic_core.core_schema import ValidationInfo
from typing_extensions import Annotated

from libecalc.common.chart_type import ChartType
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
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
    available_models: Dict["ModelName", ModelContext],
    allowed_types: List[str],
) -> str:
    if model_reference not in available_models:
        raise ModelReferenceNotFound(model_reference=model_reference)

    model = available_models[model_reference]

    if model.type not in allowed_types:
        raise InvalidModelReferenceType(model_reference=model_reference, model=model)

    return model_reference


def check_field_model_reference(allowed_types: List[str]):
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

            # Check compressor charts for simplified compressor trains
            if model.type == YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN:
                allowed_charts_simplified_trains = [ChartType.GENERIC_FROM_INPUT, ChartType.GENERIC_FROM_DESIGN_POINT]
                if hasattr(model.compressor_train, EcalcYamlKeywords.models_type_compressor_train_stages.lower()):
                    # Known compressor stages
                    for stage in model.compressor_train.stages:
                        compressor_chart = models_context[stage.compressor_chart]
                        if compressor_chart.chart_type not in allowed_charts_simplified_trains:
                            raise ValueError(
                                f"{compressor_chart.chart_type} compressor chart is not supported for {model.type}. "
                                f"Allowed charts are {', '.join(allowed_charts_simplified_trains)}."
                            )
                else:
                    # Unknown compressor stages
                    compressor_chart = models_context[model.compressor_train.compressor_chart]
                    if compressor_chart.chart_type not in allowed_charts_simplified_trains:
                        raise ValueError(
                            f"{compressor_chart.chart_type} compressor chart is not supported for {model.type}. "
                            f"Allowed charts are {', '.join(allowed_charts_simplified_trains)}."
                        )

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


CompressorV2ModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            allowed_types=[
                YamlFacilityModelType.TABULAR,
                YamlFacilityModelType.COMPRESSOR_TABULAR,
                YamlModelType.COMPRESSOR_CHART,
            ]
        )
    ),
]

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

PumpV2ModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            [
                YamlFacilityModelType.TABULAR,
                YamlFacilityModelType.PUMP_CHART_SINGLE_SPEED,
                YamlFacilityModelType.PUMP_CHART_VARIABLE_SPEED,
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
