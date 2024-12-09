from pydantic import ConfigDict, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.string.string_utils import get_duplicates
from libecalc.dto.types import FuelTypeUserDefinedCategoryType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_emission import YamlEmission


class YamlFuelType(YamlBase):
    model_config = ConfigDict(title="FuelType")

    name: str = Field(
        ...,
        title="NAME",
        description="Name of the fuel.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    category: FuelTypeUserDefinedCategoryType = CategoryField(
        None,
    )
    emissions: list[YamlEmission] = Field(
        ...,
        title="EMISSIONS",
        description="Emission types and their attributes for this fuel.\n\n$ECALC_DOCS_KEYWORDS_URL/EMISSIONS",
    )
    lower_heating_value: float = Field(
        None,
        title="LOWER_HEATING_VALUE",
        description="Warning! Deprecated. Does not have any effect. Lower heating value [MJ/Sm3] of fuel. "
        "Lower heating value is also known as net calorific value",
    )

    @field_validator("emissions", mode="after")
    @classmethod
    def ensure_unique_emission_names(cls, emissions, info: ValidationInfo):
        names = [emission.name for emission in emissions]
        duplicated_names = get_duplicates(names)

        if len(duplicated_names) > 0:
            raise ValueError(
                f"{cls.model_fields[info.field_name].alias} names must be unique."
                f" Duplicated names are: {', '.join(duplicated_names)}"
            )

        return emissions
