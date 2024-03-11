from pydantic import ConfigDict, Field

from libecalc.dto.utils.validators import EmissionNameStr
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)


class YamlEmission(YamlBase):
    model_config = ConfigDict(title="Emission")

    name: EmissionNameStr = Field(
        ...,
        title="NAME",
        description="Name of the emission.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    factor: YamlExpressionType = Field(
        ...,
        title="FACTOR",
        description="Emission factor for fuel in kg emission/Sm3 fuel. May be a constant number or an expression using vectors from a time series input.\n\n$ECALC_DOCS_KEYWORDS_URL/FACTOR",
    )
