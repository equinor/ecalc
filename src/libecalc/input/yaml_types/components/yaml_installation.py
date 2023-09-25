from typing import List, Union

from libecalc.dto.base import InstallationUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.input.yaml_types import YamlBase
from libecalc.input.yaml_types.components.legacy.yaml_fuel_consumer import (
    YamlFuelConsumer,
)
from libecalc.input.yaml_types.components.system.yaml_compressor_system import (
    YamlCompressorSystem,
)
from libecalc.input.yaml_types.components.system.yaml_pump_system import YamlPumpSystem
from libecalc.input.yaml_types.components.yaml_category_field import CategoryField
from libecalc.input.yaml_types.components.yaml_generator_set import YamlGeneratorSet
from libecalc.input.yaml_types.emitters.yaml_direct_emitter import YamlDirectEmitter
from libecalc.input.yaml_types.yaml_temporal_model import YamlTemporalModel
from pydantic import Field


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
    direct_emitters: List[YamlDirectEmitter] = Field(
        None,
        title="DIRECT_EMITTERS",
        description="Covers the direct emissions on the installation that are not consuming energy",
    )
