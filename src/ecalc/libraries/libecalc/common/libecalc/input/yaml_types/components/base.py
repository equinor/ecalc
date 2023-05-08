from typing import List, Optional

from libecalc.input.yaml_types import YamlBase
from pydantic import Field


class ConsumerBase(YamlBase):
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

    def to_dto(self, **kwargs):
        raise NotImplementedError


class OperationalConditionBase(YamlBase):
    condition: Optional[str] = Field(
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
    power_loss_factor: Optional[str] = Field(
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

    def to_dto(self):
        raise NotImplementedError


class ConsumerSystemOperationalConditionBase(OperationalConditionBase):
    conditions: Optional[str] = Field(
        None,
        title="Conditions",
        description="""
    A consumer system my have the keywords CONDITIONS which specifies conditions for the consumers to be used. \n
    At points in the time series where the condition evaluates to 0 (or False), the energy consumption will be 0. \n
    This is practical for some otherwise constant consumers, for example, fixed production loads, which have a constant \n
    load whenever there is production. CONDITIONS supports the functionality described in Expressions, \n
    but is required to evaluate to True/False or 1/0.\n
    """,
    )
    power_loss_factors: Optional[List[str]] = Field(
        None,
        title="Power loss factors",
        alias="POWERLOSSFACTORS",  # Legacy support
        description="""
    A consumer system may have list of POWER_LOSS_FACTOR that may be added to account for power transmission losses.
    E.g. if you have a subsea installation with a power line to another installation, there may be line losses. \n
    For a power line loss of 5%, POWER_LOSS_FACTOR is set to 0.05 and the power required from the power source \n
    (generator set) will be:\n\n
    power_requirement = power_before_loss / (1 - power_loss_factor)
    """,
    )
