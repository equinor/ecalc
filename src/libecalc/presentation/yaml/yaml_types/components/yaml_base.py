from typing import List, Optional

from pydantic import Field

from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types import YamlBase


class YamlConsumerBase(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Consumer name",
    )
    category: Optional[str] = Field(
        ...,
        title="CATEGORY",
        description="User defined category",
    )


class YamlOperationalConditionBase(YamlBase):
    condition: Optional[ExpressionType] = Field(
        None,
        title="Condition",
        description="""
All consumers may have a keyword CONDITION which specifies conditions for the consumer to be used. \n
At points in the time series where the condition evaluates to 0 (or False), the energy consumption will be 0. \n
This is practical for some otherwise constant consumers, for example, fixed production loads, which have a constant \n
load whenever there is production. CONDITION supports the functionality described in Expressions, \n
but is required to evaluate to True/False or 1/0.\n
""",
    )
    power_loss_factor: Optional[ExpressionType] = Field(
        None,
        title="Power loss factor",
        alias="POWERLOSSFACTOR",  # Legacy support
        description="""
A factor that may be added to account for power transmission losses. E.g. if you have a subsea installation with a \n
power line to another installation, there may be line losses. For a power line loss of 5%, POWER_LOSS_FACTOR is set to \n
0.05 and the power required from the power source (generator set) will be:\n\n
power_requirement = power_before_loss / (1 - power_loss_factor)
""",
    )


opt_expr_list = Optional[List[ExpressionType]]