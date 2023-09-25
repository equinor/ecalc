from typing import List, Optional

from libecalc.expression.expression import ExpressionType
from libecalc.input.yaml_types import YamlBase
from pydantic import Field, validator


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


class YamlConsumerSystemOperationalConditionBase(YamlBase):
    rates: List[ExpressionType] = Field(
        None,
        title="Rates",
        description="Rates [Sm3/day] as a list of expressions",
    )
    inlet_pressure: Optional[ExpressionType] = Field(
        None,
        title="Inlet pressure",
        description="Inlet pressure [bara] as a single expression"
        " This inlet pressure will be the same for all components in the consumer system.",
    )
    inlet_pressures: opt_expr_list = Field(
        None, title="Inlet pressures", description="Inlet pressures [bara] as a list of expressions."
    )
    outlet_pressure: Optional[ExpressionType] = Field(
        None,
        title="Outlet pressure",
        description="Outlet pressure [bara] as a single expression"
        " This outlet pressure will be the same for all components in the consumer system.",
    )
    outlet_pressures: opt_expr_list = Field(
        None, title="Outlet pressures", description="Outlet pressures [bara] as a list of expressions."
    )
    crossover: Optional[List[int]] = Field(
        None,
        title="Crossover",
        description=(
            "CROSSOVER specifies if rates are to be crossed over to another consumer if rate capacity is exceeded. If the energy"
            " consumption calculation is not successful for a consumer, and the consumer has a valid cross-over defined, the"
            " consumer will be allocated its maximum rate and the exceeding rate will be added to the cross-over consumer.\n"
            "To avoid loops, a consumer can only be either receiving or giving away rate. For a cross-over to be valid, the"
            ' discharge pressure at the consumer "receiving" overshooting rate must be higher than or equal to the discharge'
            ' pressure of the "sending" consumer. This is because it is possible to choke pressure down to meet the outlet pressure'
            ' in a flow line with lower pressure, but not possible to "pressure up" in the crossover flow line.\n'
            "Some examples show how the crossover logic works:\n"
            "Crossover is given as and list of integer values for the first position is the first consumer, second position is"
            " the second consumer, etc. The number specifies which consumer to send cross-over flow to, and 0 signifies no"
            " cross-over possible. Note that we use 1-index here.\n"
            "Example 1:\n"
            "Two consumers where there is a cross-over such that if the rate for the first consumer exceeds its capacity,"
            " the excess rate will be processed by the second consumer. The second consumer can not cross-over to anyone.\n"
            "CROSSOVER: [2, 0]\n"
            "Example 2:\n"
            "The first and second consumers may both send exceeding rate to the third consumer if their capacity is exceeded.\n"
            "CROSSOVER: [3,3,0]"
        ),
    )

    @validator("inlet_pressure", always=True)
    def mutually_exclusive_inlet_pressure(cls, v, values):
        if values.get("inlet_pressures") is not None and v:
            raise ValueError("'INLET_PRESSURE' and 'INLET_PRESSURES' are mutually exclusive.")
        return v

    @validator("outlet_pressure", always=True)
    def mutually_exclusive_outlet_pressure(cls, v, values):
        if values.get("outlet_pressures") is not None and v:
            raise ValueError("'OUTLET_PRESSURE' and 'OUTLET_PRESSURES' are mutually exclusive.")
        return v
