from typing import Annotated, Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.common import (
    EnergyUsageModelCommon,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    MultipleStreamsEnergyUsageModelModelReference,
)


class YamlEnergyUsageModelCompressorTrainMultipleStreams(EnergyUsageModelCommon):
    type: Annotated[
        Literal["VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES"],
        Field(
            title="TYPE",
            description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
        ),
    ]
    rate_unit: Annotated[
        Literal["SM3_PER_DAY"],
        Field(
            title="RATE_UNIT",
            description="Defaults to SM3_PER_DAY, only SM3_PER_DAY implemented for now",
        ),
    ] = "SM3_PER_DAY"
    compressor_train_model: Annotated[
        MultipleStreamsEnergyUsageModelModelReference,
        Field(
            title="COMPRESSOR_TRAIN_MODEL",
            description="The compressor train model, reference to a compressor type model defined in MODELS",
        ),
    ]
    rate_per_stream: Annotated[
        list[YamlExpressionType],
        Field(
            min_length=1,
            title="RATE_PER_STREAM",
            description="Fluid (gas) rate for each of the streams going into or out of the compressor train (excluding the outlet of the last compressor stage) in Sm3/day \n\n$ECALC_DOCS_KEYWORDS_URL/RATE",
        ),
    ]
    suction_pressure: Annotated[
        YamlExpressionType,
        Field(
            title="SUCTION_PRESSURE",
            description="Fluid (gas) pressure at compressor train inlet in bars \n\n$ECALC_DOCS_KEYWORDS_URL/SUCTION_PRESSURE",
        ),
    ]
    discharge_pressure: Annotated[
        YamlExpressionType,
        Field(
            title="DISCHARGE_PRESSURE",
            description="Fluid (gas) pressure at compressor train outlet in bars \n\n$ECALC_DOCS_KEYWORDS_URL/DISCHARGE_PRESSURE",
        ),
    ]
    interstage_control_pressure: Annotated[
        YamlExpressionType | None,
        Field(
            title="INTERSTAGE_CONTROL_PRESSURE",
            description="Fluid (gas) pressure at an intermediate step in the compressor train \n\n$ECALC_DOCS_KEYWORDS_URL/INTERSTAGE_CONTROL_PRESSURE",
        ),
    ] = None
