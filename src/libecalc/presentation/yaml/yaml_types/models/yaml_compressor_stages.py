import enum
from typing import List, Optional, Union

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    CompressorStageModelReference,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import (
    YamlPressureControl,
)


class YamlControlMarginUnits(enum.Enum):
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
    pressure_drop_ahead_of_stage: Optional[float] = Field(
        None,
        description="Pressure drop before compression stage [in bar]",
        title="PRESSURE_DROP_AHEAD_OF_STAGE",
    )
    control_margin: Optional[float] = Field(
        0.0,
        description="Surge control margin, see documentation for more details.",
        title="CONTROL_MARGIN",
    )
    control_margin_unit: Optional[YamlControlMarginUnits] = Field(
        YamlControlMarginUnits.PERCENTAGE,
        description="The unit of the surge control margin.",
        title="CONTROL_MARGIN_UNIT",
    )


class YamlCompressorStageMultipleStreams(YamlCompressorStage):
    stream: Union[str, List[str]] = Field(
        None,
        description="Reference to stream from STREAMS.",
        title="STREAM",
    )
    interstage_control_pressure: Optional[YamlInterstageControlPressure] = Field(
        None,
        description="Pressure control. Can only be specified for one (only one) of the stages 2, ..., N.",
        title="INTERSTAGE_CONTROL_PRESSURE",
    )


class YamlUnknownCompressorStages(YamlBase):
    maximum_pressure_ratio_per_stage: Optional[float] = Field(
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


class YamlCompressorStages(YamlBase):
    stages: List[YamlCompressorStage] = Field(
        ...,
        description="List of compressor stages",
        title="STAGES",
    )
