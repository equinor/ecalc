from typing import List, Literal, Optional, Union

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import (
    YamlCompressorStageMultipleStreams,
    YamlCompressorStages,
    YamlSingleSpeedCompressorStages,
    YamlUnknownCompressorStages,
    YamlVariableSpeedCompressorStages,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import (
    YamlModelType,
    YamlPressureControl,
)


class YamlCompressorTrainBase(YamlBase):
    name: str = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    maximum_power: float = Field(
        None,
        description="Optional constant MW maximum power the compressor train can require",
        title="MAXIMUM_POWER",
    )


class YamlSingleSpeedCompressorTrain(YamlCompressorTrainBase):
    type: Literal[YamlModelType.SINGLE_SPEED_COMPRESSOR_TRAIN] = Field(
        ...,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    compressor_train: YamlSingleSpeedCompressorStages = Field(
        ...,
        description="Compressor train definition",
        title="COMPRESSOR_TRAIN",
    )
    pressure_control: YamlPressureControl = Field(
        None,
        description="Method for pressure control",
        title="PRESSURE_CONTROL",
    )
    maximum_discharge_pressure: Optional[float] = Field(
        None,
        description="Maximum discharge pressure in bar (can only use if pressure control is DOWNSTREAM_CHOKE)",
        title="MAXIMUM_DISCHARGE_PRESSURE",
    )
    calculate_max_rate: Optional[bool] = Field(
        False,
        description="Optional compressor train max standard rate [Sm3/day] in result if set to true. "
        "Default false. Use with caution. This will increase runtime significantly.",
        title="CALCULATE_MAX_RATE",
    )
    power_adjustment_constant: float = Field(
        0.0,
        description="Constant to adjust power usage in MW",
        title="POWER_ADJUSTMENT_CONSTANT",
    )
    fluid_model: str = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")

    def to_dto(self):
        raise NotImplementedError


class YamlVariableSpeedCompressorTrain(YamlCompressorTrainBase):
    type: Literal[YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN] = Field(
        ...,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    compressor_train: YamlVariableSpeedCompressorStages = Field(
        ...,
        description="Compressor train definition",
        title="COMPRESSOR_TRAIN",
    )
    pressure_control: YamlPressureControl = Field(
        None,
        description="Method for pressure control",
        title="PRESSURE_CONTROL",
    )
    calculate_max_rate: Optional[bool] = Field(
        False,
        description="Optional compressor train max standard rate [Sm3/day] in result if set to true. "
        "Default false. Use with caution. This will increase runtime significantly.",
        title="CALCULATE_MAX_RATE",
    )
    power_adjustment_constant: float = Field(
        0.0,
        description="Constant to adjust power usage in MW",
        title="POWER_ADJUSTMENT_CONSTANT",
    )
    fluid_model: str = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")

    def to_dto(self):
        raise NotImplementedError


class YamlSimplifiedVariableSpeedCompressorTrain(YamlCompressorTrainBase):
    type: Literal[YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN] = Field(
        ...,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    compressor_train: Union[YamlCompressorStages, YamlUnknownCompressorStages] = Field(
        ...,
        description="Compressor train definition",
        title="COMPRESSOR_TRAIN",
    )
    calculate_max_rate: Optional[bool] = Field(
        False,
        description="Optional compressor train max standard rate [Sm3/day] in result if set to true. "
        "Default false. Use with caution. This will increase runtime significantly.",
        title="CALCULATE_MAX_RATE",
    )
    fluid_model: str = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")
    power_adjustment_constant: float = Field(
        0.0,
        description="Constant to adjust power usage in MW",
        title="POWER_ADJUSTMENT_CONSTANT",
    )

    def to_dto(self):
        raise NotImplementedError


class YamlMultipleStreamsStream(YamlBase):
    type: Literal["INGOING", "OUTGOING"]
    name: str
    fluid_model: str = Field(None, description="Reference to a fluid model", title="FLUID_MODEL")


class YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures(YamlCompressorTrainBase):
    type: Literal[YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES] = Field(
        ...,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    streams: List[YamlMultipleStreamsStream] = Field(
        ...,
        description="A list of all in- and out-going streams for the compressor train. "
        "The same equation of state (EOS) must be used for each INGOING stream fluid models",
        title="STREAMS",
    )
    stages: List[YamlCompressorStageMultipleStreams] = Field(
        ...,
        description="A list of all stages in compressor model.",
        title="STAGES",
    )
    pressure_control: YamlPressureControl = Field(
        None,
        description="Method for pressure control",
        title="PRESSURE_CONTROL",
    )
    power_adjustment_constant: float = Field(
        0.0,
        description="Constant to adjust power usage in MW",
        title="POWER_ADJUSTMENT_CONSTANT",
    )

    def to_dto(self):
        raise NotImplementedError


YamlCompressorTrain = Union[
    YamlVariableSpeedCompressorTrain,
    YamlSimplifiedVariableSpeedCompressorTrain,
    YamlSingleSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures,
]
