import enum
from typing import Literal, assert_never

from pydantic import ConfigDict

from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)


class YamlEmissionRateUnits(enum.Enum):
    KILO_PER_DAY = "KG_PER_DAY"
    TONS_PER_DAY = "TONS_PER_DAY"

    def to_unit(self) -> Unit:
        if self == YamlEmissionRateUnits.KILO_PER_DAY:
            return Unit.KILO_PER_DAY
        elif self == YamlEmissionRateUnits.TONS_PER_DAY:
            return Unit.TONS_PER_DAY

        assert_never(self)


class YamlEmissionRate(YamlBase):
    model_config = ConfigDict(title="Rate")

    value: YamlExpressionType
    unit: YamlEmissionRateUnits = YamlEmissionRateUnits.KILO_PER_DAY
    type: Literal[RateType.STREAM_DAY, RateType.CALENDAR_DAY] = RateType.STREAM_DAY


class YamlOilRateUnits(enum.Enum):
    STANDARD_CUBIC_METER_PER_DAY = "SM3_PER_DAY"

    def to_unit(self) -> Unit:
        if self == YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY:
            return Unit.STANDARD_CUBIC_METER_PER_DAY

        assert_never(self)


class YamlOilVolumeRate(YamlBase):
    model_config = ConfigDict(title="Rate")

    value: YamlExpressionType
    unit: YamlOilRateUnits = YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY
    type: Literal[RateType.STREAM_DAY, RateType.CALENDAR_DAY] = RateType.STREAM_DAY
