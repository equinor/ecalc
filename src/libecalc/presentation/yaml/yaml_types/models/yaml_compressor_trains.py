from typing import Annotated, List, Literal, Optional, Union

try:
    from pydantic.v1 import Field
except ImportError:
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
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import (
    YamlCompositionFluidModel,
    YamlPredefinedFluidModel,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream import YamlStream


class YamlCompressorTrainBase(YamlBase):
    name: str = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    fluid_model: Union[YamlPredefinedFluidModel, YamlCompositionFluidModel] = Field(
        ..., description="Reference to a fluid model", title="FLUID_MODEL"
    )
    maximum_power: Optional[
        Annotated[
            float,
            Field(
                ...,
                description="Optional constant MW maximum power the compressor train can require",
                title="MAXIMUM_POWER",
            ),
        ]
    ]


class YamlSingleSpeedCompressorTrain(YamlCompressorTrainBase):
    type: Literal[YamlModelType.SINGLE_SPEED_COMPRESSOR_TRAIN] = Field(
        YamlModelType.SINGLE_SPEED_COMPRESSOR_TRAIN,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    compressor_train: YamlSingleSpeedCompressorStages = Field(
        ...,
        description="Compressor train definition",
        title="COMPRESSOR_TRAIN",
    )
    pressure_control: YamlPressureControl = Field(
        ...,
        description="Method for pressure control",
        title="PRESSURE_CONTROL",
    )
    maximum_discharge_pressure: Optional[
        Annotated[
            float,
            Field(
                ...,
                description="Maximum discharge pressure in bar (can only use if pressure control is DOWNSTREAM_CHOKE)",
                title="MAXIMUM_DISCHARGE_PRESSURE",
            ),
        ]
    ]
    calculate_max_rate: Optional[
        Annotated[
            float,
            Field(
                ...,
                description="Optional compressor train max standard rate [Sm3/day] in result if set to true. "
                "Default false. Use with caution. This will increase runtime significantly.",
                title="CALCULATE_MAX_RATE",
            ),
        ]
    ]
    power_adjustment_constant: Optional[
        Annotated[
            float,
            Field(
                0.0,
                description="Constant to adjust power usage in MW",
                title="POWER_ADJUSTMENT_CONSTANT",
            ),
        ]
    ]

    def to_dto(self):
        raise NotImplementedError


class YamlVariableSpeedCompressorTrain(YamlCompressorTrainBase):
    type: Literal[YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN] = Field(
        YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    compressor_train: YamlVariableSpeedCompressorStages = Field(
        ...,
        description="Compressor train definition",
        title="COMPRESSOR_TRAIN",
    )
    pressure_control: YamlPressureControl = Field(
        ...,
        description="Method for pressure control",
        title="PRESSURE_CONTROL",
    )
    calculate_max_rate: Optional[
        Annotated[
            float,
            Field(
                ...,
                description="Optional compressor train max standard rate [Sm3/day] in result if set to true. "
                "Default false. Use with caution. This will increase runtime significantly.",
                title="CALCULATE_MAX_RATE",
            ),
        ]
    ]
    power_adjustment_constant: Optional[
        Annotated[
            float,
            Field(
                0.0,
                description="Constant to adjust power usage in MW",
                title="POWER_ADJUSTMENT_CONSTANT",
            ),
        ]
    ]

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
    calculate_max_rate: Optional[
        Annotated[
            float,
            Field(
                ...,
                description="Optional compressor train max standard rate [Sm3/day] in result if set to true. "
                "Default false. Use with caution. This will increase runtime significantly.",
                title="CALCULATE_MAX_RATE",
            ),
        ]
    ]

    def to_dto(self):
        raise NotImplementedError


class YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures(YamlCompressorTrainBase):
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
        title="STAGES",
    )

    def to_dto(self):
        raise NotImplementedError
