import enum
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from ecalc_neqsim_wrapper.thermo import STANDARD_PRESSURE_BARA, STANDARD_TEMPERATURE_KELVIN
from libecalc.common.utils.rates import RateType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.models import YamlFluidModel

StreamRef = str
FluidModelReference = str


class YamlStreamRateUnit(str, enum.Enum):
    SM3_PER_DAY = "SM3_PER_DAY"


class YamlInletStreamRate(YamlBase):
    model_config = ConfigDict(title="Rate")

    value: YamlExpressionType
    unit: Annotated[
        YamlStreamRateUnit,
        Field(
            title="UNIT",
            description="Rate unit. SM3_PER_DAY for standard volume.",
        ),
    ]
    type: Literal[RateType.STREAM_DAY, RateType.CALENDAR_DAY] = RateType.STREAM_DAY

    condition: Annotated[
        YamlExpressionType | None,
        Field(
            title="CONDITION",
            description="A logical condition that determines whether the venting emitter emission rate is applicable. "
            "This condition must evaluate to true for the rate to be used.\n\n"
            "For more details, see: $ECALC_DOCS_KEYWORDS_URL/CONDITION",
        ),
    ] = None
    conditions: Annotated[
        list[YamlExpressionType] | None,
        Field(
            title="CONDITIONS",
            description="A list of logical conditions that collectively determine whether the venting emitter emission rate is applicable. "
            "All conditions in the list must evaluate to true for the rate to be used.\n\n"
            "For more details, see: $ECALC_DOCS_KEYWORDS_URL/CONDITION",
        ),
    ] = None

    @model_validator(mode="after")
    def validate_condition(self):
        self._check_mutually_exclusive_condition()
        self._check_non_empty_conditions()
        return self

    def _check_mutually_exclusive_condition(self):
        if self.conditions is not None and self.condition is not None:
            raise ValueError("Either CONDITION or CONDITIONS should be specified, not both.")

    def _check_non_empty_conditions(self):
        if self.conditions is not None and len(self.conditions) == 0:
            raise ValueError("CONDITIONS cannot be an empty list.")


class YamlInletStream(YamlBase):
    """
    Represents an inlet stream definition that can be referenced by process system and stream distribution.
    """

    name: Annotated[
        StreamRef,
        Field(
            title="NAME",
            description="Unique name of the inlet stream.",
        ),
    ]
    fluid_model: Annotated[
        FluidModelReference | YamlFluidModel,
        Field(
            title="FLUID_MODEL",
            description="Reference to a fluid model (e.g. defined in MODELS/FLUID_MODELS elsewhere).",
        ),
    ]

    temperature: Annotated[
        YamlExpressionType,
        Field(
            title="TEMPERATURE",
            description="Temperature in K. Optional; defaults to standard temperature if omitted.",
        ),
    ] = STANDARD_TEMPERATURE_KELVIN
    pressure: Annotated[
        YamlExpressionType,
        Field(
            title="PRESSURE",
            description="Pressure in Pa. Optional; defaults to standard pressure if omitted.",
        ),
    ] = STANDARD_PRESSURE_BARA

    rate: Annotated[
        YamlInletStreamRate,
        Field(
            title="RATE",
            description="Rate with unit + value.",
        ),
    ]
