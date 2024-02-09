from typing import Literal, Optional

from pydantic import ConfigDict, Field

from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types import YamlBase


class YamlTimeSeries(YamlBase):
    value: ExpressionType
    unit: Unit


class YamlRate(YamlTimeSeries):
    model_config = ConfigDict(title="Rate")

    unit: Unit = Unit.STANDARD_CUBIC_METER_PER_DAY
    type: Literal[RateType.STREAM_DAY, RateType.CALENDAR_DAY] = RateType.STREAM_DAY


class YamlEmissionRate(YamlTimeSeries):
    model_config = ConfigDict(title="Rate")

    unit: Literal[Unit.KILO_PER_DAY, Unit.TONS_PER_DAY] = Unit.KILO_PER_DAY
    type: Literal[RateType.STREAM_DAY, RateType.CALENDAR_DAY] = RateType.STREAM_DAY


class YamlPressure(YamlTimeSeries):
    model_config = ConfigDict(title="Pressure")

    unit: Unit = Unit.BARA


class YamlTemperature(YamlTimeSeries):
    model_config = ConfigDict(title="Temperature")

    unit: Unit = Unit.KELVIN


class YamlDensity(YamlTimeSeries):
    model_config = ConfigDict(title="Density")

    unit: Unit = Unit.KG_SM3


class YamlStreamConditions(YamlBase):
    model_config = ConfigDict(title="Stream")

    rate: Optional[YamlRate] = Field(
        None,
        title="Rate",
        description="Rate...",
    )
    pressure: Optional[YamlPressure] = Field(
        None,
        title="Pressure",
        description="Pressure..",
    )
    temperature: Optional[YamlTemperature] = Field(
        None,
        title="Temperature",
        description="Temperature...",
    )
    fluid_density: Optional[YamlDensity] = Field(None, title="Fluid density", description="The fluid density...")
    # fluid model
    # At least one should be specified, rate or pressure? temperature, fluid model when multistream? fluid density for pumps?
