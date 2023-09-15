from typing import List

from libecalc.dto.base import FuelTypeUserDefinedCategoryType
from libecalc.expression.expression import ExpressionType
from libecalc.input.yaml_types import YamlBase
from libecalc.input.yaml_types.components.yaml_category_field import CategoryField
from libecalc.input.yaml_types.fuel_type.yaml_emission import YamlEmission
from pydantic import Field


class YamlFuelType(YamlBase):
    class Config:
        title = "FuelType"

    name: str = Field(
        ...,
        title="NAME",
        description="Name of the fuel.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    price: ExpressionType = Field(
        None,
        title="PRICE",
        description="Price or sales value of fuel in NOK per Sm3.\n\n$ECALC_DOCS_KEYWORDS_URL/PRICE",
    )
    category: FuelTypeUserDefinedCategoryType = CategoryField(
        None,
    )
    emissions: List[YamlEmission] = Field(
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
