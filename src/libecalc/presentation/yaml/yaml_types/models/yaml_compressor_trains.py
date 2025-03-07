from typing import Literal, Union

from pydantic import Field, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    FluidModelReference,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import (
    YamlCompressorStage,
    YamlCompressorStageMultipleStreams,
    YamlCompressorStages,
    YamlCompressorStageWithMarginAndPressureDrop,
    YamlUnknownCompressorStages,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import (
    YamlChartType,
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
    compressor_train: YamlCompressorStages[YamlCompressorStageWithMarginAndPressureDrop] = Field(
        ...,
        description="Compressor train definition",
        title="COMPRESSOR_TRAIN",
    )
    pressure_control: YamlPressureControl = Field(
        YamlPressureControl.DOWNSTREAM_CHOKE,
        description="Method for pressure control",
        title="PRESSURE_CONTROL",
    )
    maximum_discharge_pressure: float | None = Field(
        None,
        description="Maximum discharge pressure in bar (can only use if pressure control is DOWNSTREAM_CHOKE)",
        title="MAXIMUM_DISCHARGE_PRESSURE",
    )
    calculate_max_rate: bool | None = Field(
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
    power_adjustment_factor: float = Field(
        1.0,
        description="Factor to adjust power usage in MW",
        title="POWER_ADJUSTMENT_FACTOR",
    )
    fluid_model: FluidModelReference = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")

    def to_dto(self):
        raise NotImplementedError


class YamlVariableSpeedCompressorTrain(YamlCompressorTrainBase):
    type: Literal[YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN] = Field(
        ...,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    compressor_train: YamlCompressorStages[YamlCompressorStageWithMarginAndPressureDrop] = Field(
        ...,
        description="Compressor train definition",
        title="COMPRESSOR_TRAIN",
    )
    pressure_control: YamlPressureControl = Field(
        YamlPressureControl.DOWNSTREAM_CHOKE,
        description="Method for pressure control",
        title="PRESSURE_CONTROL",
    )
    calculate_max_rate: bool | None = Field(
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
    power_adjustment_factor: float = Field(
        1.0,
        description="Factor to adjust power usage in MW",
        title="POWER_ADJUSTMENT_FACTOR",
    )
    fluid_model: FluidModelReference = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")

    def to_dto(self):
        raise NotImplementedError


class YamlSimplifiedVariableSpeedCompressorTrain(YamlCompressorTrainBase):
    type: Literal[YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN] = Field(
        ...,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    compressor_train: YamlCompressorStages[YamlCompressorStage] | YamlUnknownCompressorStages = Field(
        ...,
        description="Compressor train definition",
        title="COMPRESSOR_TRAIN",
    )
    calculate_max_rate: bool | None = Field(
        False,
        description="Optional compressor train max standard rate [Sm3/day] in result if set to true. "
        "Default false. Use with caution. This will increase runtime significantly.",
        title="CALCULATE_MAX_RATE",
    )
    fluid_model: FluidModelReference = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")
    power_adjustment_constant: float = Field(
        0.0,
        description="Constant to adjust power usage in MW",
        title="POWER_ADJUSTMENT_CONSTANT",
    )
    power_adjustment_factor: float = Field(
        1.0,
        description="Factor to adjust power usage in MW",
        title="POWER_ADJUSTMENT_FACTOR",
    )

    def to_dto(self):
        raise NotImplementedError

    @model_validator(mode="after")
    def check_compressor_chart(self, info: ValidationInfo):
        if info.context is not None:
            train = info.context["model_types"][self.name].compressor_train
            allowed_charts_simplified_trains = [
                YamlChartType.GENERIC_FROM_INPUT.value,
                YamlChartType.GENERIC_FROM_DESIGN_POINT.value,
            ]
            # If known compressor stages
            if hasattr(train, EcalcYamlKeywords.models_type_compressor_train_stages.lower()):
                for stage in train.stages:
                    compressor_chart = info.context["model_types"][stage.compressor_chart]

                    if compressor_chart.chart_type not in allowed_charts_simplified_trains:
                        raise ValueError(
                            f"{compressor_chart.chart_type.value} compressor chart is not supported for {self.type.value}. "
                            f"Allowed charts are {', '.join(allowed_charts_simplified_trains)}."
                        )
            else:
                # Unknown compressor stages
                compressor_chart = info.context["model_types"][train.compressor_chart]
                if compressor_chart.chart_type not in allowed_charts_simplified_trains:
                    raise ValueError(
                        f"{compressor_chart.chart_type} compressor chart is not supported for {self.type}. "
                        f"Allowed charts are {', '.join(allowed_charts_simplified_trains)}."
                    )
        return self


class YamlMultipleStreamsStream(YamlBase):
    type: Literal["INGOING", "OUTGOING"]
    name: str
    fluid_model: FluidModelReference | None = Field(None, description="Reference to a fluid model", title="FLUID_MODEL")


class YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures(YamlCompressorTrainBase):
    type: Literal[YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES] = Field(
        ...,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    streams: list[YamlMultipleStreamsStream] = Field(
        ...,
        description="A list of all in- and out-going streams for the compressor train. "
        "The same equation of state (EOS) must be used for each INGOING stream fluid models",
        title="STREAMS",
    )
    stages: list[YamlCompressorStageMultipleStreams] = Field(
        ...,
        description="A list of all stages in compressor model.",
        title="STAGES",
    )
    pressure_control: YamlPressureControl = Field(
        YamlPressureControl.DOWNSTREAM_CHOKE,
        description="Method for pressure control",
        title="PRESSURE_CONTROL",
    )
    power_adjustment_constant: float = Field(
        0.0,
        description="Constant to adjust power usage in MW",
        title="POWER_ADJUSTMENT_CONSTANT",
    )
    power_adjustment_factor: float = Field(
        1.0,
        description="Factor to adjust power usage in MW",
        title="POWER_ADJUSTMENT_FACTOR",
    )

    def to_dto(self):
        raise NotImplementedError


YamlCompressorTrain = Union[
    YamlVariableSpeedCompressorTrain,
    YamlSimplifiedVariableSpeedCompressorTrain,
    YamlSingleSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures,
]

YamlCompatibleTrainsControlMargin = [
    EcalcYamlKeywords.models_type_compressor_train_single_speed,
    EcalcYamlKeywords.models_type_compressor_train_variable_speed,
    EcalcYamlKeywords.models_type_compressor_train_variable_speed_multiple_streams_and_pressures,
]

YamlCompatibleTrainsPressureDropAheadOfStage = [
    EcalcYamlKeywords.models_type_compressor_train_single_speed,
    EcalcYamlKeywords.models_type_compressor_train_variable_speed,
    EcalcYamlKeywords.models_type_compressor_train_variable_speed_multiple_streams_and_pressures,
]
