from pydantic import ConfigDict, Field, model_validator

from libecalc.dto.types import InstallationUserDefinedCategoryType
from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_fuel_consumer import (
    YamlFuelConsumer,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_generator_set import (
    YamlGeneratorSet,
)
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlInstallation(YamlBase):
    model_config = ConfigDict(title="Installation")

    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Name of the installation.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    category: InstallationUserDefinedCategoryType = CategoryField(None)
    hydrocarbon_export: YamlTemporalModel[YamlExpressionType] = Field(
        0,
        title="HCEXPORT",
        description="Defines the export of hydrocarbons as number of oil equivalents in Sm3.\n\n$ECALC_DOCS_KEYWORDS_URL/HCEXPORT",
        alias="HCEXPORT",
    )
    fuel: YamlTemporalModel[str] = Field(
        None,
        title="FUEL",
        description="Main fuel type for installation.\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL",
    )
    regularity: YamlTemporalModel[YamlExpressionType] = Field(
        1,
        title="REGULARITY",
        description="Regularity of the installation can be specified by a single number or as an expression. USE WITH CARE.\n\n$ECALC_DOCS_KEYWORDS_URL/REGULARITY",
    )
    generator_sets: list[YamlGeneratorSet] | None = Field(
        None,
        title="GENERATORSETS",
        description="Defines one or more generator sets.\n\n$ECALC_DOCS_KEYWORDS_URL/GENERATORSETS",
        alias="GENERATORSETS",
    )
    fuel_consumers: list[YamlFuelConsumer] | None = Field(
        None,
        title="FUELCONSUMERS",
        description="Defines fuel consumers on the installation which are not generators.\n\n$ECALC_DOCS_KEYWORDS_URL/FUELCONSUMERS",
        alias="FUELCONSUMERS",
    )
    venting_emitters: list[YamlVentingEmitter] | None = Field(
        None,
        title="VENTING_EMITTERS",
        description="Covers the direct emissions on the installation that are not consuming energy",
    )

    @model_validator(mode="after")
    def check_some_consumer_or_emitter(self):
        if self.fuel_consumers or self.venting_emitters or self.generator_sets:
            return self
        else:
            raise ValueError(
                f"Keywords are missing:\n It is required to specify at least one of the keywords "
                f"{EcalcYamlKeywords.fuel_consumers}, {EcalcYamlKeywords.generator_sets} or {EcalcYamlKeywords.installation_venting_emitters} in the model.",
            ) from None
