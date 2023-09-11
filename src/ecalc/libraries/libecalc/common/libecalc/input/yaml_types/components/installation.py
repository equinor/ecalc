from libecalc.dto.base import InstallationUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.input.yaml_types import YamlBase
from libecalc.input.yaml_types.components.category import CategoryField
from libecalc.input.yaml_types.placeholder_type import PlaceholderType
from libecalc.input.yaml_types.temporal_model import TemporalModel
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
    generatorsets: PlaceholderType = Field(
        None,
        title="GENERATORSETS",
        description="Defines one or more generator sets.\n\n$ECALC_DOCS_KEYWORDS_URL/GENERATORSETS",
    )
    fuelconsumers: PlaceholderType = Field(
        None,
        title="FUELCONSUMERS",
        description="Defines fuel consumers on the installation which are not generators.\n\n$ECALC_DOCS_KEYWORDS_URL/FUELCONSUMERS",
    )
    directemitters: PlaceholderType = Field(
        None,
        title="DIRECTEMITTERS",
        description="Covers the direct emissions on the installation that are not consuming energy",
    )
