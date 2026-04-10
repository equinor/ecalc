from enum import Enum
from typing import Annotated

from pydantic import ConfigDict, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.string.string_utils import get_duplicates
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import CategoryField
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_emission import YamlEmission


class FuelTypeUserDefinedCategoryType(str, Enum):
    FUEL_GAS = "FUEL-GAS"
    DIESEL = "DIESEL"


class YamlFuelType(YamlBase):
    model_config = ConfigDict(title="FuelType")

    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Name of the fuel.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
        ),
    ]
    category: FuelTypeUserDefinedCategoryType = CategoryField(
        None,
    )
    emissions: Annotated[
        list[YamlEmission],
        Field(
            title="EMISSIONS",
            description="Emission types and their attributes for this fuel.\n\n$ECALC_DOCS_KEYWORDS_URL/EMISSIONS",
        ),
    ]
    lower_heating_value: Annotated[
        float | None,
        Field(
            description="Warning! Deprecated. Does not have any effect. Lower heating value [MJ/Sm3] of fuel. "
            "Lower heating value is also known as net calorific value",
        ),
    ] = None

    @field_validator("emissions", mode="after")
    @classmethod
    def ensure_unique_emission_names(cls, emissions, info: ValidationInfo):
        names = [emission.name for emission in emissions]
        duplicated_names = get_duplicates(names)

        if len(duplicated_names) > 0:
            raise ValueError(
                f"{cls.model_fields[info.field_name].alias} names must be unique."  # type: ignore[index]
                f" Duplicated names are: {', '.join(duplicated_names)}"
            )

        return emissions
