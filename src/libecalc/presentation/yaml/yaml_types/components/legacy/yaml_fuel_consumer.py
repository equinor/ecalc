from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.energy_model_validation import (
    validate_energy_usage_models,
)
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model import (
    YamlFuelEnergyUsageModel,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlFuelConsumer(YamlBase):
    model_config = ConfigDict(title="FUEL_CONSUMER")

    component_type: Literal["FUEL_CONSUMER"] = Field(
        "FUEL_CONSUMER",
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
    category: YamlTemporalModel[ConsumerUserDefinedCategoryType] = CategoryField(...)
    energy_usage_model: YamlTemporalModel[YamlFuelEnergyUsageModel] = Field(
        ...,
        title="ENERGY_USAGE_MODEL",
        description="Definition of the energy usage model for the consumer."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/ENERGY_USAGE_MODEL",
    )

    fuel: YamlTemporalModel[str] = Field(
        None,
        title="FUEL",
        description="The fuel used by the consumer." "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL",
    )

    @model_validator(mode="after")
    def check_energy_usage_models(self):
        _check_multiple_energy_usage_models = validate_energy_usage_models(self.energy_usage_model, self.name)
        return self
