from typing import Any, Dict, List, Type, Union

from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.input.yaml_types import YamlBase
from libecalc.input.yaml_types.components.legacy.yaml_electricity_consumer import (
    YamlElectricityConsumer,
)
from libecalc.input.yaml_types.components.system.yaml_compressor_system import (
    YamlCompressorSystem,
)
from libecalc.input.yaml_types.components.system.yaml_pump_system import YamlPumpSystem
from libecalc.input.yaml_types.components.yaml_category_field import CategoryField
from libecalc.input.yaml_types.yaml_placeholder_type import YamlPlaceholderType
from libecalc.input.yaml_types.yaml_schema_helpers import (
    replace_temporal_placeholder_property_with_legacy_ref,
)
from libecalc.input.yaml_types.yaml_temporal_model import YamlTemporalModel
from pydantic import Field


class YamlGeneratorSet(YamlBase):
    class Config:
        title = "GeneratorSet"

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
    fuel: YamlTemporalModel[str] = Field(
        None,
        title="FUEL",
        description="The fuel used by the generator set." "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL",
    )
    electricity2fuel: YamlTemporalModel[YamlPlaceholderType] = Field(
        ...,
        title="ELECTRICITY2FUEL",
        description="Specifies the correlation between the electric power delivered and the fuel burned by a "
        "generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/ELECTRICITY2FUEL",
    )
    consumers: List[Union[YamlElectricityConsumer, YamlCompressorSystem, YamlPumpSystem]] = Field(
        ...,
        title="CONSUMERS",
        description="Consumers getting electrical power from the generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/CONSUMERS",
    )
