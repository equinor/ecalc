from typing import Literal

from pydantic import ConfigDict, Field

from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model import (
    YamlElectricityEnergyUsageModel,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlElectricityConsumer(YamlBase):
    model_config = ConfigDict(title="ELECTRICITY_CONSUMER")

    component_type: Literal["ELECTRICITY_CONSUMER"] = Field(
        "ELECTRICITY_CONSUMER",
        title="Type",
        description="The type of the component",
        alias="TYPE",
        exclude=True,
    )

    name: str = Field(
        ...,
        title="NAME",
        description="Name of the consumer.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    category: ConsumerUserDefinedCategoryType = CategoryField(...)
    energy_usage_model: YamlTemporalModel[YamlElectricityEnergyUsageModel] = Field(
        ...,
        title="ENERGY_USAGE_MODEL",
        description="Definition of the energy usage model for the consumer."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/ENERGY_USAGE_MODEL",
    )
