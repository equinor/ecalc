from typing import Any, Dict, List, Type, Union

from libecalc.dto.base import InstallationUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.input.yaml_types import YamlBase
from libecalc.input.yaml_types.components.legacy.yaml_fuel_consumer import (
    YamlFuelConsumer,
)
from libecalc.input.yaml_types.components.yaml_category_field import CategoryField
from libecalc.input.yaml_types.components.yaml_compressor_system import (
    YamlCompressorSystem,
)
from libecalc.input.yaml_types.components.yaml_generator_set import YamlGeneratorSet
from libecalc.input.yaml_types.components.yaml_pump_system import YamlPumpSystem
from libecalc.input.yaml_types.yaml_placeholder_type import YamlPlaceholderType
from libecalc.input.yaml_types.yaml_schema_helpers import (
    replace_placeholder_property_with_legacy_ref,
)
from libecalc.input.yaml_types.yaml_temporal_model import YamlTemporalModel
from pydantic import Field


class YamlInstallation(YamlBase):  # TODO: conditional required, either fuelconsumers or gensets
    class Config:
        title = "Installation"

        @staticmethod
        def schema_extra(schema: Dict[str, Any], model: Type["YamlInstallation"]) -> None:
            replace_placeholder_property_with_legacy_ref(
                schema=schema,
                property_key="DIRECTEMITTERS",
                property_ref="$SERVER_NAME/api/v1/schema-validation/direct-emitters.json#definitions/DIRECTEMITTERS",
            )

    name: str = Field(
        ...,
        title="NAME",
        description="Name of the installation.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    category: InstallationUserDefinedCategoryType = CategoryField(None)
    hcexport: YamlTemporalModel[Expression] = Field(
        ...,
        title="HCEXPORT",
        description="Defines the export of hydrocarbons as number of oil equivalents in Sm3.\n\n$ECALC_DOCS_KEYWORDS_URL/HCEXPORT",
    )
    fuel: YamlTemporalModel[str] = Field(
        None,
        title="FUEL",
        description="Main fuel type for installation." "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL",
    )
    regularity: YamlTemporalModel[Expression] = Field(
        None,
        title="REGULARITY",
        description="Regularity of the installation can be specified by a single number or as an expression. USE WITH CARE.\n\n$ECALC_DOCS_KEYWORDS_URL/REGULARITY",
    )
    generatorsets: List[YamlGeneratorSet] = Field(
        None,
        title="GENERATORSETS",
        description="Defines one or more generator sets.\n\n$ECALC_DOCS_KEYWORDS_URL/GENERATORSETS",
    )
    fuelconsumers: List[Union[YamlFuelConsumer, YamlCompressorSystem, YamlPumpSystem]] = Field(
        None,
        title="FUELCONSUMERS",
        description="Defines fuel consumers on the installation which are not generators.\n\n$ECALC_DOCS_KEYWORDS_URL/FUELCONSUMERS",
    )
    directemitters: YamlPlaceholderType = Field(
        None,
        title="DIRECTEMITTERS",
        description="Covers the direct emissions on the installation that are not consuming energy",
    )
