from typing import List, Union

from pydantic import ConfigDict, Field
from typing_extensions import Annotated

from libecalc.common.discriminator_fallback import DiscriminatorWithFallback
from libecalc.dto.base import InstallationUserDefinedCategoryType
from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_fuel_consumer import (
    YamlFuelConsumer,
)
from libecalc.presentation.yaml.yaml_types.components.system.yaml_consumer_system import (
    YamlConsumerSystem,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_generator_set import (
    YamlGeneratorSet,
)
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlInstallation(YamlBase):  # TODO: conditional required, either fuelconsumers or gensets
    model_config = ConfigDict(title="Installation")

    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Name of the installation.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    category: InstallationUserDefinedCategoryType = CategoryField(None)
    hydrocarbon_export: YamlTemporalModel[Expression] = Field(
        None,
        title="HCEXPORT",
        description="Defines the export of hydrocarbons as number of oil equivalents in Sm3.\n\n$ECALC_DOCS_KEYWORDS_URL/HCEXPORT",
        alias="HCEXPORT",
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
    generator_sets: List[YamlGeneratorSet] = Field(
        None,
        title="GENERATORSETS",
        description="Defines one or more generator sets.\n\n$ECALC_DOCS_KEYWORDS_URL/GENERATORSETS",
        alias="GENERATORSETS",
    )
    fuel_consumers: List[
        Annotated[
            Union[
                YamlFuelConsumer,
                YamlConsumerSystem,
            ],
            Field(discriminator="component_type"),
            DiscriminatorWithFallback("TYPE", "FUEL_CONSUMER"),
        ]
    ] = Field(
        None,
        title="FUELCONSUMERS",
        description="Defines fuel consumers on the installation which are not generators.\n\n$ECALC_DOCS_KEYWORDS_URL/FUELCONSUMERS",
        alias="FUELCONSUMERS",
    )
    venting_emitters: List[YamlVentingEmitter] = Field(
        None,
        title="VENTING_EMITTERS",
        description="Covers the direct emissions on the installation that are not consuming energy",
    )
