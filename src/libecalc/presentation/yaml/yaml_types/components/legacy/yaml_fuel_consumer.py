from typing import Any, Dict, Type

from pydantic import Field

from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_placeholder_type import (
    YamlPlaceholderType,
)
from libecalc.presentation.yaml.yaml_types.yaml_schema_helpers import (
    replace_temporal_placeholder_property_with_legacy_ref,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlFuelConsumer(YamlBase):
    class Config:
        title = "FUEL_CONSUMER"

        @staticmethod
        def schema_extra(schema: Dict[str, Any], model: Type["YamlFuelConsumer"]) -> None:
            replace_temporal_placeholder_property_with_legacy_ref(
                schema=schema,
                property_key="ENERGY_USAGE_MODEL",
                property_ref="$SERVER_NAME/api/v1/schema-validation/energy-usage-model.json#properties/ENERGY_USAGE_MODEL",
            )

    name: str = Field(
        ...,
        title="NAME",
        description="Name of the consumer.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    category: ConsumerUserDefinedCategoryType = CategoryField(...)
    energy_usage_model: YamlTemporalModel[YamlPlaceholderType] = Field(
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