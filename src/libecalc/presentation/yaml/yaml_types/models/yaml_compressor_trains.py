from typing import List, Literal, Union

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import (
    YamlCompressorStageMultipleStreams,
    YamlCompressorStages,
    YamlUnknownCompressorStages,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import (
    YamlModelType,
    YamlPressureControl,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream import YamlStream


class YamlCompressorTrainBase(YamlBase):
    name: str = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    fluid_model: str = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")
    pressure_control: YamlPressureControl = Field(
        ...,
        description="Method for pressure control",
        title="PRESSURE_CONTROL",
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


class YamlSingleSpeedCompressorTrain(YamlCompressorTrainBase):
    type: Literal[YamlModelType.SINGLE_SPEED_COMPRESSOR_TRAIN] = Field(
        YamlModelType.SINGLE_SPEED_COMPRESSOR_TRAIN,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    maximum_discharge_pressure: str = Field(
        ...,
        description="Maximum discharge pressure in bar (can only use if pressure control is DOWNSTREAM_CHOKE)",
        title="MAXIMUM_DISCHARGE_PRESSURE",
    )
    compressor_train: YamlCompressorStages = Field(
        ...,
        description="Compressor train definition",
        title="COMPRESSOR_TRAIN",
    )

    def to_dto(self):
        raise NotImplementedError


class YamlVariableSpeedCompressorTrain(YamlCompressorTrainBase):
    type: Literal[YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN] = Field(
        YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    compressor_train: YamlCompressorStages = Field(
        ...,
        description="Compressor train definition",
        title="COMPRESSOR_TRAIN",
    )

    def to_dto(self):
        raise NotImplementedError


class YamlSimplifiedVariableSpeedCompressorTrain(YamlCompressorTrainBase):
    type: Literal[YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN] = Field(
        YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    compressor_train: Union[YamlCompressorStages, YamlUnknownCompressorStages] = Field(
        ...,
        description="Compressor train definition",
        title="COMPRESSOR_TRAIN",
    )

    def to_dto(self):
        raise NotImplementedError


class YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures(YamlCompressorTrainBase):
    name: str = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES] = Field(
        YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    streams: List[YamlStream] = Field(
        ...,
        description="A list of all in- and out-going streams for the compressor train. "
        "The same equation of state (EOS) must be used for each INGOING stream fluid models",
        title="STREAMS",
    )
    stages: List[YamlCompressorStageMultipleStreams] = Field(
        ...,
        description="A list of all stages in compressor model.",
        title="STREAMS",
    )

    maximum_power: str = Field(
        ..., description="Optional constant MW maximum power the compressor train can require", title="MAXIMUM_POWER"
    )

    def to_dto(self):
        raise NotImplementedError
