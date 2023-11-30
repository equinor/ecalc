import enum
from typing import List, Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlCompressorChart,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import (
    YamlModelType,
)


class YamlPressureControl(enum.Enum):
    DOWNSTREAM_CHOKE = "DOWNSTREAM_CHOKE"
    UPSTREAM_CHOKE = "UPSTREAM_CHOKE"
    INDIVIDUAL_ASV_PRESSURE = "INDIVIDUAL_ASV_PRESSURE"
    INDIVIDUAL_ASV_RATE = "INDIVIDUAL_ASV_RATE"
    COMMON_ASV = "COMMON_ASV"


class YamlCompressorStage(YamlBase):
    inlet_temperature: str = Field(
        ...,
        description="Inlet temperature in Celsius for stage",
        title="INLET_TEMPERATURE",
    )
    compressor_chart: YamlCompressorChart = Field(
        ...,
        description="Reference to compressor chart model for stage, must be defined in MODELS or FACILITY_INPUTS",
        title="COMPRESSOR_CHART",
    )
    pressure_drop_ahead_of_stage: str = Field(
        ...,
        description="Pressure drop before compression stage [in bar]",
        title="PRESSURE_DROP_AHEAD_OF_STAGE",
    )


class YamlSingleSpeedCompressorTrain(YamlBase):
    name: str = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.SINGLE_SPEED_COMPRESSOR_TRAIN] = Field(
        YamlModelType.SINGLE_SPEED_COMPRESSOR_TRAIN,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    fluid_model: str = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")
    pressure_control: YamlPressureControl = Field(
        ...,
        description="Method for pressure control",
        title="PRESSURE_CONTROL",
    )
    maximum_discharge_pressure: str = Field(
        ...,
        description="Maximum discharge pressure in bar (can only use if pressure control is DOWNSTREAM_CHOKE)",
        title="MAXIMUM_DISCHARGE_PRESSURE",
    )
    power_adjustment_constant: float = Field(
        0.0,
        description="Constant to adjust power usage in MW",
        title="POWER_ADJUSTMENT_CONSTANT",
    )
    maximum_power: str = Field(
        ..., description="Optional constant MW maximum power the compressor train can require", title="MAXIMUM_POWER"
    )
    calculate_max_rate: str = Field(
        ...,
        description="Optional compressor train max standard rate [Sm3/day] in result if set to true. "
        "Default false. Use with caution. This will increase runtime significantly.",
        title="CALCULATE_MAX_RATE",
    )
    stages: List[YamlCompressorStage]
