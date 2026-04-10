import enum
from typing import Annotated, Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.common import (
    EnergyUsageModelCommon,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)


class ConsumptionRateType(enum.Enum):
    STREAM_DAY = "STREAM_DAY"
    CALENDAR_DAY = "CALENDAR_DAY"


class YamlEnergyUsageModelDirectFuel(EnergyUsageModelCommon):
    type: Annotated[
        Literal["DIRECT"],
        Field(
            title="TYPE",
            description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
        ),
    ]
    consumption_rate_type: Annotated[
        ConsumptionRateType,
        Field(
            title="CONSUMPTION_RATE_TYPE",
            description="Defines the energy usage rate as stream day or calendar day.\n\n$ECALC_DOCS_KEYWORDS_URL/CONSUMPTION_RATE_TYPE#consumption-rate-type",
        ),
    ] = None
    fuel_rate: YamlExpressionType = Field(
        ...,
        title="FUEL_RATE",
        description="Fixed power consumer with constant load.\n\n$ECALC_DOCS_KEYWORDS_URL/LOAD",
        alias="FUELRATE",
    )


class YamlEnergyUsageModelDirectElectricity(EnergyUsageModelCommon):
    type: Annotated[
        Literal["DIRECT"],
        Field(
            title="TYPE",
            description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
        ),
    ]
    consumption_rate_type: Annotated[
        ConsumptionRateType,
        Field(
            title="CONSUMPTION_RATE_TYPE",
            description="Defines the energy usage rate as stream day or calendar day.\n\n$ECALC_DOCS_KEYWORDS_URL/CONSUMPTION_RATE_TYPE#consumption-rate-type",
        ),
    ] = None
    load: Annotated[
        YamlExpressionType,
        Field(
            title="LOAD",
            description="Fixed power consumer with constant load.\n\n$ECALC_DOCS_KEYWORDS_URL/LOAD",
        ),
    ]
