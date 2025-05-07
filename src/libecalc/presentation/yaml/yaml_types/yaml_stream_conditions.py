import enum
from typing import Literal, assert_never

from pydantic import ConfigDict, Field, model_validator

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

    condition: YamlExpressionType | None = Field(
        None,
        title="CONDITION",
        description="A logical condition that determines whether the venting emitter emission rate is applicable. "
        "This condition must evaluate to true for the rate to be used.\n\n"
        "For more details, see: $ECALC_DOCS_KEYWORDS_URL/CONDITION",
    )
    conditions: list[YamlExpressionType] | None = Field(
        None,
        title="CONDITIONS",
        description="A list of logical conditions that collectively determine whether the venting emitter emission rate is applicable. "
        "All conditions in the list must evaluate to true for the rate to be used.\n\n"
        "For more details, see: $ECALC_DOCS_KEYWORDS_URL/CONDITION",
    )

    @model_validator(mode="after")
    def validate(self):
        self._check_mutually_exclusive_condition()
        self._check_non_empty_conditions()
        return self

    def _check_mutually_exclusive_condition(self):
        if self.conditions is not None and self.condition is not None:
            raise ValueError("Either CONDITION or CONDITIONS should be specified, not both.")

    def _check_non_empty_conditions(self):
        if self.conditions is not None and len(self.conditions) == 0:
            raise ValueError("CONDITIONS cannot be an empty list.")


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

    condition: YamlExpressionType | None = Field(
        None,
        title="CONDITION",
        description="A logical condition that determines whether the venting emitter oil volume rate is applicable. "
        "This condition must evaluate to true for the rate to be used.\n\n"
        "For more details, see: $ECALC_DOCS_KEYWORDS_URL/CONDITION",
    )
    conditions: list[YamlExpressionType] | None = Field(
        None,
        title="CONDITIONS",
        description="A list of logical conditions that collectively determine whether the venting emitter oil volume rate is applicable. "
        "All conditions in the list must evaluate to true for the rate to be used.\n\n"
        "For more details, see: $ECALC_DOCS_KEYWORDS_URL/CONDITION",
    )

    @model_validator(mode="after")
    def validate(self):
        self._check_mutually_exclusive_condition()
        self._check_non_empty_conditions()
        return self

    def _check_mutually_exclusive_condition(self):
        if self.conditions is not None and self.condition is not None:
            raise ValueError("Either CONDITION or CONDITIONS should be specified, not both.")

    def _check_non_empty_conditions(self):
        if self.conditions is not None and len(self.conditions) == 0:
            raise ValueError("CONDITIONS cannot be an empty list.")
