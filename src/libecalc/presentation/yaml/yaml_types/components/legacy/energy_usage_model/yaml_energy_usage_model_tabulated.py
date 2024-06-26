from typing import List, Literal

from pydantic import AfterValidator, Field
from typing_extensions import Annotated

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.common import (
    EnergyUsageModelCommon,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlFacilityModelType,
)
from libecalc.presentation.yaml.yaml_types.models.model_reference import ModelName
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    check_field_model_reference,
)


class YamlTabulatedVariable(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of variable. Must correspond exactly to header/column name in the energy function",
    )
    expression: YamlExpressionType = Field(
        ...,
        title="EXPRESSION",
        description="Expression defining the variable",
    )


ModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            allowed_types=[
                YamlFacilityModelType.TABULAR,
            ]
        )
    ),
]


class YamlEnergyUsageModelTabulated(EnergyUsageModelCommon):
    type: Literal["TABULATED"] = Field(
        ...,
        title="TYPE",
        description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )
    energy_function: ModelReference = Field(
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
