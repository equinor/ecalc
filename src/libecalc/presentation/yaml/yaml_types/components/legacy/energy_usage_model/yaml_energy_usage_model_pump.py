from typing import Annotated, Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.common import (
    EnergyUsageModelCommon,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    PumpEnergyUsageModelModelReference,
)


class YamlEnergyUsageModelPump(EnergyUsageModelCommon):
    type: Annotated[
        Literal["PUMP"],
        Field(
            title="TYPE",
            description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
        ),
    ]
    energy_function: PumpEnergyUsageModelModelReference = Field(
        ...,
        title="ENERGY_FUNCTION",
        description="The pump energy function, reference to a pump type facility model defined in FACILITY_INPUTS",
        alias="ENERGYFUNCTION",
    )
    rate: Annotated[
        YamlExpressionType | None,
        Field(
            title="RATE",
            description="Fluid rate through the pump in Sm3/day \n\n$ECALC_DOCS_KEYWORDS_URL/RATE",
        ),
    ] = None
    suction_pressure: Annotated[
        YamlExpressionType | None,
        Field(
            title="SUCTION_PRESSURE",
            description="Fluid pressure at pump inlet in bars \n\n$ECALC_DOCS_KEYWORDS_URL/SUCTION_PRESSURE",
        ),
    ] = None
    discharge_pressure: Annotated[
        YamlExpressionType | None,
        Field(
            title="DISCHARGE_PRESSURE",
            description="Fluid pressure at pump outlet in bars \n\n$ECALC_DOCS_KEYWORDS_URL/DISCHARGE_PRESSURE",
        ),
    ] = None
    fluid_density: Annotated[
        YamlExpressionType,
        Field(
            title="FLUID_DENSITY",
            description="Density of the fluid in kg/m3. \n\n$ECALC_DOCS_KEYWORDS_URL/FLUID_DENSITY",
        ),
    ]
