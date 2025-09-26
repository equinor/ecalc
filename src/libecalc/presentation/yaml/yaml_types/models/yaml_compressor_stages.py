import enum
from typing import Generic, TypeVar, Union

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    CompressorStageModelReference,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import (
    YamlPressureControl,
)


class YamlControlMarginUnits(str, enum.Enum):
    FRACTION = "FRACTION"
    PERCENTAGE = "PERCENTAGE"


class YamlInterstageControlPressure(YamlBase):
    upstream_pressure_control: YamlPressureControl = Field(
        ...,
        description="Pressure control.",
        title="UPSTREAM_PRESSURE_CONTROL",
    )
    downstream_pressure_control: YamlPressureControl = Field(
        ...,
        description="Pressure control.",
        title="DOWNSTREAM_PRESSURE_CONTROL",
    )


class YamlStageEfficiencyLoss(YamlBase):
    """
    Describes additional losses for a compressor stage that increase the calculated power and energy usage,
    without changing the efficiency value itself.

    The losses are applied as:
        power_with_losses = (power * factor) + constant
        energy_usage_with_losses = (energy_usage * factor) + constant

    - factor: Multiplicative increase to power and energy usage (default 1.0).
    - constant: Additive increase to power and energy usage (default 0.0).
    """

    factor: YamlExpressionType = Field(
        None,
        description="Multiplicative factor applied to the calculated power and energy usage for this stage, "
        "representing additional real-world losses. Defaults to 1.0 if not specified.",
        title="FACTOR",
    )
    constant: YamlExpressionType = Field(
        None,
        description="Additive constant applied to the calculated power and energy usage for this stage, "
        "representing fixed extra losses. Defaults to 0.0 if not specified.",
        title="CONSTANT",
    )


class YamlCompressorStage(YamlBase):
    inlet_temperature: float = Field(
        ...,
        description="Inlet temperature in Celsius for stage",
        title="INLET_TEMPERATURE",
    )
    compressor_chart: CompressorStageModelReference = Field(
        ...,
        description="Reference to compressor chart model for stage, must be defined in MODELS or FACILITY_INPUTS",
        title="COMPRESSOR_CHART",
    )
    efficiency_loss: YamlStageEfficiencyLoss = Field(
        None,
        description="Describes losses that increase the calculated power and energy usage for a compressor stage, "
        "without changing the efficiency value itself. The factor applies a multiplicative increase, and the constant "
        "adds a fixed extra loss. This represents real-world effects such as mechanical, leakage, or heat losses that "
        "require more power than the ideal calculation.",
        title="EFFICIENCY_LOSS",
    )


class YamlCompressorStageWithMarginAndPressureDrop(YamlCompressorStage):
    pressure_drop_ahead_of_stage: float = Field(
        0.0,
        description="Pressure drop before compression stage [in bar]",
        title="PRESSURE_DROP_AHEAD_OF_STAGE",
    )
    control_margin: float = Field(
        ge=0,
        description="Surge control margin, see documentation for more details.",
        title="CONTROL_MARGIN",
    )
    control_margin_unit: YamlControlMarginUnits = Field(
        ...,
        description="The unit of the surge control margin.",
        title="CONTROL_MARGIN_UNIT",
    )


class YamlCompressorStageMultipleStreams(YamlCompressorStageWithMarginAndPressureDrop):
    stream: list[str] | None = Field(
        None,
        description="Reference to stream from STREAMS.",
        title="STREAM",
    )
    interstage_control_pressure: YamlInterstageControlPressure | None = Field(
        None,
        description="Pressure control. Can only be specified for one (only one) of the stages 2, ..., N.",
        title="INTERSTAGE_CONTROL_PRESSURE",
    )


class YamlUnknownCompressorStages(YamlBase):
    maximum_pressure_ratio_per_stage: float | None = Field(
        None,
        description="Maximum pressure ratio per stage. Number of compressors will be large enough to ensure no "
        "pressure ratios are above a given maximum pressure ratio per stage, but not larger",
        title="MAXIMUM_PRESSURE_RATIO_PER_STAGE",
    )
    inlet_temperature: float = Field(
        ...,
        description="Inlet temperature in Celsius for stage",
        title="INLET_TEMPERATURE",
    )
    compressor_chart: CompressorStageModelReference = Field(
        ...,
        description="Reference to compressor chart model for stage, must be defined in MODELS or FACILITY_INPUTS",
        title="COMPRESSOR_CHART",
    )


TStage = TypeVar("TStage", bound=Union[YamlCompressorStage, YamlCompressorStageWithMarginAndPressureDrop])


class YamlCompressorStages(YamlBase, Generic[TStage]):
    stages: list[TStage] = Field(
        ...,
        description="List of compressor stages",
        title="STAGES",
    )
