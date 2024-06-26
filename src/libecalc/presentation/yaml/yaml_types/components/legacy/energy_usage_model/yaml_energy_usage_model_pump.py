from typing import Literal

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
    type: Literal["PUMP"] = Field(
        ...,
        title="TYPE",
        description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )
    energy_function: PumpEnergyUsageModelModelReference = Field(
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
