from typing import List, Literal

from pydantic import Field

from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.common import (
    EnergyUsageModelCommon,
)


class YamlTabulatedVariable(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of variable. Must correspond exactly to header/column name in the energy function",
    )
    expression: ExpressionType = Field(
        ...,
        title="EXPRESSION",
        description="Expression defining the variable",
    )


class YamlEnergyUsageModelTabulated(EnergyUsageModelCommon):
    type: Literal["TABULATED"] = Field(
        ...,
        title="TYPE",
        description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )
    energy_function: str = Field(
        ...,
        title="ENERGY_FUNCTION",
        description="The tabulated energy function, reference to a tabular type facility model defined in FACILITY_INPUTS",
        alias="ENERGYFUNCTION",
    )
    variables: List[YamlTabulatedVariable] = Field(
        ...,
        title="VARIABLES",
        description="Variables for the tabulated energy function \n\n$ECALC_DOCS_KEYWORDS_URL/VARIABLES#variables",
    )
