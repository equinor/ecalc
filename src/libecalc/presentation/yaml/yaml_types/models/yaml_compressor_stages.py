import enum
from typing import Generic, TypeVar, Union

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
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


class YamlCompressorStageWithMarginAndPressureDrop(YamlCompressorStage):
    pressure_drop_ahead_of_stage: float | None = Field(
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
    stream: str | list[str] = Field(
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
