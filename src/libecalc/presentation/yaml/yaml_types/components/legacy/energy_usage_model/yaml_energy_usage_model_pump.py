from typing import Literal

from pydantic import AfterValidator, Field
from typing_extensions import Annotated

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

ModelReference = Annotated[
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


class YamlEnergyUsageModelPump(EnergyUsageModelCommon):
    type: Literal["PUMP"] = Field(
        ...,
        title="TYPE",
        description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )
    energy_function: ModelReference = Field(
        ...,
        title="ENERGY_FUNCTION",
        description="The pump energy function, reference to a pump type facility model defined in FACILITY_INPUTS",
        alias="ENERGYFUNCTION",
    )
    rate: YamlExpressionType = Field(
        None,
        title="RATE",
        description="Fluid rate through the pump in Sm3/day \n\n$ECALC_DOCS_KEYWORDS_URL/RATE",
    )
    suction_pressure: YamlExpressionType = Field(
        None,
        title="SUCTION_PRESSURE",
        description="Fluid pressure at pump inlet in bars \n\n$ECALC_DOCS_KEYWORDS_URL/SUCTION_PRESSURE",
    )
    discharge_pressure: YamlExpressionType = Field(
        None,
        title="DISCHARGE_PRESSURE",
        description="Fluid pressure at pump outlet in bars \n\n$ECALC_DOCS_KEYWORDS_URL/DISCHARGE_PRESSURE",
    )
    fluid_density: YamlExpressionType = Field(
        ...,
        title="FLUID_DENSITY",
        description="Density of the fluid in kg/m3. \n\n$ECALC_DOCS_KEYWORDS_URL/FLUID_DENSITY",
    )
