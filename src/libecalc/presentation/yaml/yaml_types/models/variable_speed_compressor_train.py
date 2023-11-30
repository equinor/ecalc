from typing import List, Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import (
    YamlModelType,
    YamlPressureControl,
)
from libecalc.presentation.yaml.yaml_types.yaml_compressor_stage import (
    YamlCompressorStage,
)


class YamlVariableSpeedCompressorTrain(YamlBase):
    name: str = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN] = Field(
        YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
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
    stages: List[YamlCompressorStage]

    def to_dto(self):
        raise NotImplementedError
