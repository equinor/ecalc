from typing import List

from pydantic import Field

from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types import YamlBase


class EnergyUsageModelCommon(YamlBase):
    condition: ExpressionType = Field(
        None,
        title="CONDITION",
        description="Logical condition for the consumer to be used.\n\n$ECALC_DOCS_KEYWORDS_URL/CONDITION",
    )
    conditions: List[ExpressionType] = Field(
        None,
        title="CONDITIONS",
        description="Logical conditions for the consumer to be used.\n\n$ECALC_DOCS_KEYWORDS_URL/CONDITION",
    )
    power_loss_factor: ExpressionType = Field(
        None,
        title="POWERLOSSFACTOR",
        description="A factor that may be added to account for power line losses.\n\n$ECALC_DOCS_KEYWORDS_URL/POWERLOSSFACTOR",
        alias="POWERLOSSFACTOR",
    )
