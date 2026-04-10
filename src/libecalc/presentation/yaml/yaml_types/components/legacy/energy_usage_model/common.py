from typing import Annotated

from pydantic import Field, model_validator

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)


class EnergyUsageModelCommon(YamlBase):
    condition: Annotated[
        YamlExpressionType,
        Field(
            title="CONDITION",
            description="Logical condition for the consumer to be used.\n\n$ECALC_DOCS_KEYWORDS_URL/CONDITION",
        ),
    ] = None
    conditions: Annotated[
        list[YamlExpressionType] | None,
        Field(
            title="CONDITIONS",
            description="Logical conditions for the consumer to be used.\n\n$ECALC_DOCS_KEYWORDS_URL/CONDITION",
        ),
    ] = None
    power_loss_factor: YamlExpressionType = Field(
        None,
        title="POWERLOSSFACTOR",
        description="A factor that may be added to account for power line losses.\n\n$ECALC_DOCS_KEYWORDS_URL/POWERLOSSFACTOR",
        alias="POWERLOSSFACTOR",
    )

    @model_validator(mode="after")
    def check_mutually_exclusive_condition(self):
        if self.conditions is not None and self.condition is not None:
            raise ValueError("Either CONDITION or CONDITIONS should be specified, not both.")
        return self
