import enum
from typing import Literal, Optional, assert_never

from pydantic import ConfigDict, Field

from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)


class YamlTimeSeries(YamlBase):
    value: YamlExpressionType
    unit: Unit


class YamlRate(YamlTimeSeries):
    model_config = ConfigDict(title="Rate")

    unit: Unit = Unit.STANDARD_CUBIC_METER_PER_DAY
    type: Literal[RateType.STREAM_DAY, RateType.CALENDAR_DAY] = RateType.STREAM_DAY


class YamlEmissionRateUnits(enum.Enum):
    KILO_PER_DAY = "KG_PER_DAY"
    TONS_PER_DAY = "TONS_PER_DAY"

    def to_unit(self) -> Unit:
        if self == YamlEmissionRateUnits.KILO_PER_DAY:
            return Unit.KILO_PER_DAY
        elif self == YamlEmissionRateUnits.TONS_PER_DAY:
            return Unit.TONS_PER_DAY

        assert_never(self)


class YamlEmissionRate(YamlTimeSeries):
    model_config = ConfigDict(title="Rate")
    unit: YamlEmissionRateUnits = YamlEmissionRateUnits.KILO_PER_DAY
    type: Literal[RateType.STREAM_DAY, RateType.CALENDAR_DAY] = RateType.STREAM_DAY


class YamlOilRateUnits(enum.Enum):
    STANDARD_CUBIC_METER_PER_DAY = "SM3_PER_DAY"

    def to_unit(self) -> Unit:
        if self == YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY:
            return Unit.STANDARD_CUBIC_METER_PER_DAY

        assert_never(self)


class YamlOilVolumeRate(YamlTimeSeries):
    model_config = ConfigDict(title="Rate")

    unit: YamlOilRateUnits = YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY
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
