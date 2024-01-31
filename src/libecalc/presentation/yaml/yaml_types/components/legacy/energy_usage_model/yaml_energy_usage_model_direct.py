import enum
from typing import Literal

from pydantic import Field

from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.common import (
    EnergyUsageModelCommon,
)


class ConsumptionRateType(enum.Enum):
    STREAM_DAY = "STREAM_DAY"
    CALENDAR_DAY = "CALENDAR_DAY"


class YamlEnergyUsageModelDirect(EnergyUsageModelCommon):
    type: Literal["DIRECT"] = Field(
        ...,
        title="TYPE",
        description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )
    load: ExpressionType = Field(
        None,
        title="LOAD",
        description="Fixed power consumer with constant load.\n\n$ECALC_DOCS_KEYWORDS_URL/LOAD",
    )
    fuel_rate: ExpressionType = Field(
        None,
        title="FUEL_RATE",
        description="Fixed power consumer with constant load.\n\n$ECALC_DOCS_KEYWORDS_URL/LOAD",
        alias="FUELRATE",
    )
    consumption_rate_type: ConsumptionRateType = Field(
        None,
        title="CONSUMPTION_RATE_TYPE",
        description="Defines the energy usage rate as stream day or calendar day.\n\n$ECALC_DOCS_KEYWORDS_URL/CONSUMPTION_RATE_TYPE#consumption-rate-type",
    )
