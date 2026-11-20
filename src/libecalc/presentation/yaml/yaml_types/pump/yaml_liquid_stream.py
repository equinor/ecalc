import enum
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from libecalc.common.utils.rates import RateType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType


class YamlLiquidStreamRateUnit(enum.StrEnum):
    M3_PER_DAY = "M3_PER_DAY"


class YamlLiquidStreamRate(YamlBase):
    model_config = ConfigDict(title="LIQUID_STREAM_RATE")

    value: Annotated[YamlExpressionType, Field(title="VALUE", description="Liquid volume rate.")]
    unit: Annotated[YamlLiquidStreamRateUnit, Field(title="UNIT", description="Rate unit. M3_PER_DAY.")]
    type: Annotated[
        Literal[RateType.STREAM_DAY],
        Field(title="TYPE", description="Type of rate. Only STREAM_DAY is supported."),
    ] = RateType.STREAM_DAY


class YamlLiquidInletStream(YamlBase):
    """A liquid stream into a pump simulation."""

    model_config = ConfigDict(title="LIQUID_INLET_STREAM")

    name: Annotated[str, Field(title="NAME", description="Name of the inlet stream.")]
    pressure: Annotated[YamlExpressionType, Field(title="PRESSURE", description="Pressure [bara].")]
    density: Annotated[YamlExpressionType, Field(title="DENSITY", description="Liquid density [kg/m3].")]
    rate: Annotated[YamlLiquidStreamRate, Field(title="RATE", description="Liquid rate.")]
