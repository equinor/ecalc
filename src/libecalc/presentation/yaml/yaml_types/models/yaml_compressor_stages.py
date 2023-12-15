import enum
from typing import Annotated, List, Optional, Union

try:
    from pydantic.v1 import Field
except ImportError:
    from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlGenericFromDesignPointChart,
    YamlGenericFromInputChart,
    YamlSingleSpeedChart,
    YamlVariableSpeedChart,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlPressureControl


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


class YamlCompressorStageBase(YamlBase):
    inlet_temperature: float = Field(
        ...,
        description="Inlet temperature in Celsius for stage",
        title="INLET_TEMPERATURE",
    )
    compressor_chart: Union[
        YamlSingleSpeedChart, YamlVariableSpeedChart, YamlGenericFromDesignPointChart, YamlGenericFromInputChart
    ] = Field(
        ...,
        description="Reference to compressor chart model for stage, must be defined in MODELS or FACILITY_INPUTS",
        title="COMPRESSOR_CHART",
    )


class YamlSingleSpeedCompressorStage(YamlCompressorStageBase):
    pressure_drop_ahead_of_stage: Optional[
        Annotated[
            float,
            Field(
                ...,
                description="Pressure drop before compression stage [in bar]",
                title="PRESSURE_DROP_AHEAD_OF_STAGE",
            ),
        ]
    ]
    compressor_chart: YamlSingleSpeedChart


class YamlVariableSpeedCompressorStage(YamlCompressorStageBase):
    pressure_drop_ahead_of_stage: Optional[
        Annotated[
            float,
            Field(
                ...,
                description="Pressure drop before compression stage [in bar]",
                title="PRESSURE_DROP_AHEAD_OF_STAGE",
            ),
        ]
    ]
    compressor_chart: YamlVariableSpeedChart


class YamlCompressorStage(YamlCompressorStageBase):
    pressure_drop_ahead_of_stage: Optional[
        Annotated[
            float,
            Field(
                ...,
                description="Pressure drop before compression stage [in bar]",
                title="PRESSURE_DROP_AHEAD_OF_STAGE",
            ),
        ]
    ]


class YamlCompressorStageMultipleStreams(YamlCompressorStageBase):
    control_margin: Optional[
        Annotated[
            float,
            Field(
                0.0,
                description="Surge control margin, see documentation for more details.",
                title="CONTROL_MARGIN",
            ),
        ]
    ]
    control_margin_unit: Optional[
        Annotated[
            YamlControlMarginUnits,
            Field(
                YamlControlMarginUnits.PERCENTAGE,
                description="The unit of the surge control margin.",
                title="CONTROL_MARGIN_UNIT",
            ),
        ]
    ]
    stream: Union[str, List[str]] = Field(
        ...,
        description="Reference to stream from STREAMS.",
        title="STREAM",
    )
    pressure_drop_ahead_of_stage: Optional[
        Annotated[
            float,
            Field(
                ...,
                description="Pressure drop before compression stage [in bar]",
                title="PRESSURE_DROP_AHEAD_OF_STAGE",
            ),
        ]
    ]
    interstage_control_pressure: Optional[
        Annotated[
            YamlInterstageControlPressure,
            Field(
                ...,
                description="Pressure control. Can only be specified for one (only one) of the stages 2, ..., N.",
                title="INTERSTAGE_CONTROL_PRESSURE",
            ),
        ]
    ]


class YamlUnknownCompressorStages(YamlCompressorStageBase):
    maximum_pressure_ratio_per_stage: Optional[
        Annotated[
            float,
            Field(
                ...,
                description="Maximum pressure ratio per stage. Number of compressors will be large enough to ensure no "
                "pressure ratios are above a given maximum pressure ratio per stage, but not larger",
                title="MAXIMUM_PRESSURE_RATIO_PER_STAGE",
            ),
        ]
    ]


class YamlCompressorStages(YamlBase):
    stages: List[YamlCompressorStage] = Field(
        ...,
        description="List of compressor stages",
        title="STAGES",
    )


class YamlSingleSpeedCompressorStages(YamlBase):
    stages: List[YamlSingleSpeedCompressorStage] = Field(
        ...,
        description="List of compressor stages",
        title="STAGES",
    )


class YamlVariableSpeedCompressorStages(YamlBase):
    stages: List[YamlVariableSpeedCompressorStage] = Field(
        ...,
        description="List of compressor stages",
        title="STAGES",
    )
