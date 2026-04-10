from typing import Annotated, Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.common import (
    EnergyUsageModelCommon,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    CompressorEnergyUsageModelModelReference,
)


class YamlEnergyUsageModelCompressor(EnergyUsageModelCommon):
    type: Annotated[
        Literal["COMPRESSOR"],
        Field(
            title="TYPE",
            description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
        ),
    ]
    energy_function: CompressorEnergyUsageModelModelReference = Field(
        ...,
        title="ENERGY_FUNCTION",
        description="The compressor energy function, reference to a compressor type facility model defined in FACILITY_INPUTS",
        alias="ENERGYFUNCTION",
    )
    rate: Annotated[
        YamlExpressionType,
        Field(
            title="RATE",
            description="Fluid (gas) rate through the compressor in Sm3/day \n\n$ECALC_DOCS_KEYWORDS_URL/RATE",
        ),
    ]
    suction_pressure: Annotated[
        YamlExpressionType,
        Field(
            title="SUCTION_PRESSURE",
            description="Fluid (gas) pressure at compressor inlet in bars \n\n$ECALC_DOCS_KEYWORDS_URL/SUCTION_PRESSURE",
        ),
    ] = None
    discharge_pressure: Annotated[
        YamlExpressionType,
        Field(
            title="DISCHARGE_PRESSURE",
            description="Fluid (gas) pressure at compressor outlet in bars \n\n$ECALC_DOCS_KEYWORDS_URL/DISCHARGE_PRESSURE",
        ),
    ] = None
