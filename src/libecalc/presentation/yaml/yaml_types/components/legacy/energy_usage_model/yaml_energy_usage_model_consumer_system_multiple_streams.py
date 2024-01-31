from typing import List, Literal

from pydantic import Field

from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.common import (
    EnergyUsageModelCommon,
)


class YamlEnergyUsageModelCompressorTrainMultipleStreams(EnergyUsageModelCommon):
    type: Literal["VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES"] = Field(
        ...,
        title="TYPE",
        description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )
    rate_unit: Literal["SM3_PER_DAY"] = Field(
        "SM3_PER_DAY",
        title="RATE_UNIT",
        description="Defaults to SM3_PER_DAY, only SM3_PER_DAY implemented for now",
    )
    compressor_train_model: str = Field(
        ...,
        title="COMPRESSOR_TRAIN_MODEL",
        description="The compressor train model, reference to a compressor type model defined in MODELS",
    )
    rate_per_stream: List[ExpressionType] = Field(
        ...,
        title="RATE_PER_STREAM",
        description="Fluid (gas) rate for each of the streams going into or out of the compressor train (excluding the outlet of the last compressor stage) in Sm3/day \n\n$ECALC_DOCS_KEYWORDS_URL/RATE",
    )
    suction_pressure: ExpressionType = Field(
        ...,
        title="SUCTION_PRESSURE",
        description="Fluid (gas) pressure at compressor train inlet in bars \n\n$ECALC_DOCS_KEYWORDS_URL/SUCTION_PRESSURE",
    )
    discharge_pressure: ExpressionType = Field(
        ...,
        title="DISCHARGE_PRESSURE",
        description="Fluid (gas) pressure at compressor train outlet in bars \n\n$ECALC_DOCS_KEYWORDS_URL/DISCHARGE_PRESSURE",
    )
    interstage_control_pressure: ExpressionType = Field(
        None,
        title="INTERSTAGE_CONTROL_PRESSURE",
        description="Fluid (gas) pressure at an intermediate step in the compressor train \n\n$ECALC_DOCS_KEYWORDS_URL/INTERSTAGE_CONTROL_PRESSURE",
    )
