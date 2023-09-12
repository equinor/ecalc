from typing import Any, Dict, List, Type

from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.input.yaml_types import YamlBase
from libecalc.input.yaml_types.components.category import CategoryField
from libecalc.input.yaml_types.components.legacy.yaml_electricity_consumer import (
    YamlElectricityConsumer,
)
from libecalc.input.yaml_types.placeholder_type import PlaceholderType
from libecalc.input.yaml_types.schema_helpers import (
    replace_temporal_placeholder_property_with_legacy_ref,
)
from libecalc.input.yaml_types.temporal_model import TemporalModel
from pydantic import Field


class YamlGeneratorSet(YamlBase):
    class Config:
        title = "GENERATORSET"

        @staticmethod
        def schema_extra(schema: Dict[str, Any], model: Type["YamlGeneratorSet"]) -> None:
            replace_temporal_placeholder_property_with_legacy_ref(
                schema=schema,
                property_key="ELECTRICITY2FUEL",
                property_ref="$SERVER_NAME/api/v1/schema-validation/energy-usage-model-common.json#definitions/number_or_string",
            )

    name: str = Field(
        ...,
        title="NAME",
        description="Name of the generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    category: ConsumerUserDefinedCategoryType = CategoryField(...)
    fuel: TemporalModel[str] = Field(
        None,
        title="FUEL",
        description="The fuel used by the generator set." "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL",
    )
    electricity2fuel: TemporalModel[PlaceholderType] = Field(
        ...,
        title="ELECTRICITY2FUEL",
        description="Specifies the correlation between the electric power delivered and the fuel burned by a "
        "generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/ELECTRICITY2FUEL",
    )
    consumers: List[YamlElectricityConsumer] = Field(
        ...,
        title="CONSUMERS",
        description="Consumers getting electrical power from the generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/CONSUMERS",
    )
