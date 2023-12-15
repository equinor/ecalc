from typing import List, Union

try:
    from pydantic.v1 import Field
except ImportError:
    from pydantic import Field

from libecalc.dto.base import InstallationUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_fuel_consumer import (
    YamlFuelConsumer,
)
from libecalc.presentation.yaml.yaml_types.components.system.yaml_consumer_system import (
    YamlConsumerSystem,
)
from libecalc.presentation.yaml.yaml_types.components.train.yaml_train import YamlTrain
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_compressor import (
    YamlCompressor,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_generator_set import (
    YamlGeneratorSet,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_pump import YamlPump
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlInstallation(YamlBase):  # TODO: conditional required, either fuelconsumers or gensets
    class Config:
        title = "Installation"

    name: str = Field(
        ...,
        title="NAME",
        description="Name of the installation.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    category: InstallationUserDefinedCategoryType = CategoryField(None)
    hcexport: YamlTemporalModel[Expression] = Field(
        None,
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
    fuelconsumers: List[
        Union[
            YamlFuelConsumer,
            YamlConsumerSystem[YamlCompressor],
            YamlConsumerSystem[YamlPump],
            YamlConsumerSystem[YamlTrain[YamlCompressor]],
        ]
    ] = Field(
        None,
        title="FUELCONSUMERS",
        description="Defines fuel consumers on the installation which are not generators.\n\n$ECALC_DOCS_KEYWORDS_URL/FUELCONSUMERS",
    )
    venting_emitters: List[YamlVentingEmitter] = Field(
        None,
        title="VENTING_EMITTERS",
        description="Covers the direct emissions on the installation that are not consuming energy",
    )
