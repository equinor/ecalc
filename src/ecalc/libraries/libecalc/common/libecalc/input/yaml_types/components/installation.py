from typing import Any, Dict, List, Type, Union

from libecalc.dto.base import InstallationUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.input.yaml_types import YamlBase
from libecalc.input.yaml_types.components.category import CategoryField
from libecalc.input.yaml_types.components.compressor_system import CompressorSystem
from libecalc.input.yaml_types.components.generator_set import YamlGeneratorSet
from libecalc.input.yaml_types.components.legacy.yaml_fuel_consumer import (
    YamlFuelConsumer,
)
from libecalc.input.yaml_types.components.pump_system import PumpSystem
from libecalc.input.yaml_types.placeholder_type import PlaceholderType
from libecalc.input.yaml_types.schema_helpers import (
    replace_placeholder_property_with_legacy_ref,
)
from libecalc.input.yaml_types.temporal_model import TemporalModel
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
    hcexport: TemporalModel[Expression] = Field(
        ...,
        title="HCEXPORT",
        description="Defines the export of hydrocarbons as number of oil equivalents in Sm3.\n\n$ECALC_DOCS_KEYWORDS_URL/HCEXPORT",
    )
    fuel: TemporalModel[str] = Field(
        None,
        title="FUEL",
        description="Main fuel type for installation." "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL",
    )
    regularity: TemporalModel[Expression] = Field(
        None,
        title="REGULARITY",
        description="Regularity of the installation can be specified by a single number or as an expression. USE WITH CARE.\n\n$ECALC_DOCS_KEYWORDS_URL/REGULARITY",
    )
    generatorsets: List[YamlGeneratorSet] = Field(
        None,
        title="GENERATORSETS",
        description="Defines one or more generator sets.\n\n$ECALC_DOCS_KEYWORDS_URL/GENERATORSETS",
    )
    fuelconsumers: List[Union[YamlFuelConsumer, CompressorSystem, PumpSystem]] = Field(
        None,
        title="FUELCONSUMERS",
        description="Defines fuel consumers on the installation which are not generators.\n\n$ECALC_DOCS_KEYWORDS_URL/FUELCONSUMERS",
    )
    directemitters: PlaceholderType = Field(
        None,
        title="DIRECTEMITTERS",
        description="Covers the direct emissions on the installation that are not consuming energy",
    )
