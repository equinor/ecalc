from libecalc.expression.expression import ExpressionType
from libecalc.input.yaml_types import YamlBase
from pydantic import Field


class YamlEmission(YamlBase):
    class Config:
        title = "Emission"

    name: str = Field(
        ...,
        title="NAME",
        description="Name of the emission.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    factor: ExpressionType = Field(
        ...,
        title="FACTOR",
        description="Emission factor for fuel in kg emission/Sm3 fuel. May be a constant number or an expression using vectors from a time series input.\n\n$ECALC_DOCS_KEYWORDS_URL/FACTOR",
    )
    tax: ExpressionType = Field(
        None,
        title="TAX",
        description="Emission tax per volume fuel burned, i.e. NOK/Sm3 fuel. May be a constant number or an expression using vectors from a time series input.\n\n$ECALC_DOCS_KEYWORDS_URL/TAX",
    )
    quota: ExpressionType = Field(
        None,
        title="QUOTA",
        description="Emission tax per kg emission emitted, i.e. NOK/kg emission. May be a constant number or an expression using vectors from a time series input.\n\n$ECALC_DOCS_KEYWORDS_URL/QUOTA",
    )
