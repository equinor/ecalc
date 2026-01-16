import logging
from typing import Annotated, Literal, Union

from pydantic import Field, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.model_reference import ModelName
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    FluidModelReference,
    ShaftReference,
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

logger = logging.getLogger(__name__)


class YamlCompressorTrainBase(YamlBase):
    name: ModelName = Field(
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
    calculate_max_rate: bool = Field(
        False,
        description="Optional compressor train max standard rate [Sm3/day] in result if set to true. "
        "Default false. Use with caution. This will increase runtime significantly.",
        title="CALCULATE_MAX_RATE",
    )
    power_adjustment_constant: float = Field(
        0.0,
        description="[DEPRECATED] Constant to adjust power usage in MW. Use SHAFT with MECHANICAL_EFFICIENCY instead.",
        title="POWER_ADJUSTMENT_CONSTANT",
    )
    power_adjustment_factor: float = Field(
        1.0,
        description="[DEPRECATED] Factor to adjust power usage in MW. Use SHAFT with MECHANICAL_EFFICIENCY instead.",
        title="POWER_ADJUSTMENT_FACTOR",
    )
    fluid_model: FluidModelReference = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")
    shaft: ShaftReference | None = Field(
        None,
        description="Reference to a SHAFT model that defines mechanical efficiency for this compressor train. "
        "If not specified, an implicit shaft with mechanical efficiency of 1.0 is used.",
        title="SHAFT",
    )

    @model_validator(mode="after")
    def validate_shaft_and_legacy_params(self):
        """Validate mutual exclusivity of SHAFT and legacy power adjustment parameters."""
        has_shaft = self.shaft is not None
        has_legacy_factor = self.power_adjustment_factor != 1.0
        has_legacy_constant = self.power_adjustment_constant != 0.0

        if has_shaft and (has_legacy_factor or has_legacy_constant):
            raise ValueError(
                f"Model '{self.name}': Cannot specify both SHAFT and POWER_ADJUSTMENT_FACTOR/POWER_ADJUSTMENT_CONSTANT. "
                "Use SHAFT with MECHANICAL_EFFICIENCY instead of legacy power adjustment parameters."
            )

        if has_legacy_factor or has_legacy_constant:
            logger.warning(
                f"Model '{self.name}': POWER_ADJUSTMENT_FACTOR and POWER_ADJUSTMENT_CONSTANT are deprecated "
                "and will be removed in a future version. Use SHAFT with MECHANICAL_EFFICIENCY instead. "
                "See migration guide: https://equinor.github.io/ecalc/changelog/migration/mechanical-efficiency"
            )

        return self

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
        description="[DEPRECATED] Constant to adjust power usage in MW. Use SHAFT with MECHANICAL_EFFICIENCY instead.",
        title="POWER_ADJUSTMENT_CONSTANT",
    )
    power_adjustment_factor: float = Field(
        1.0,
        description="[DEPRECATED] Factor to adjust power usage in MW. Use SHAFT with MECHANICAL_EFFICIENCY instead.",
        title="POWER_ADJUSTMENT_FACTOR",
    )
    fluid_model: FluidModelReference = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")
    shaft: ShaftReference | None = Field(
        None,
        description="Reference to a SHAFT model that defines mechanical efficiency for this compressor train. "
        "If not specified, an implicit shaft with mechanical efficiency of 1.0 is used.",
        title="SHAFT",
    )

    @model_validator(mode="after")
    def validate_shaft_and_legacy_params(self):
        """Validate mutual exclusivity of SHAFT and legacy power adjustment parameters."""
        has_shaft = self.shaft is not None
        has_legacy_factor = self.power_adjustment_factor != 1.0
        has_legacy_constant = self.power_adjustment_constant != 0.0

        if has_shaft and (has_legacy_factor or has_legacy_constant):
            raise ValueError(
                f"Model '{self.name}': Cannot specify both SHAFT and POWER_ADJUSTMENT_FACTOR/POWER_ADJUSTMENT_CONSTANT. "
                "Use SHAFT with MECHANICAL_EFFICIENCY instead of legacy power adjustment parameters."
            )

        if has_legacy_factor or has_legacy_constant:
            logger.warning(
                f"Model '{self.name}': POWER_ADJUSTMENT_FACTOR and POWER_ADJUSTMENT_CONSTANT are deprecated "
                "and will be removed in a future version. Use SHAFT with MECHANICAL_EFFICIENCY instead. "
                "See migration guide: https://equinor.github.io/ecalc/changelog/migration/mechanical-efficiency"
            )

        return self

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
    calculate_max_rate: bool = Field(
        False,
        description="Optional compressor train max standard rate [Sm3/day] in result if set to true. "
        "Default false. Use with caution. This will increase runtime significantly.",
        title="CALCULATE_MAX_RATE",
    )
    fluid_model: FluidModelReference = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")
    mechanical_efficiency: float = Field(
        1.0,
        description="Mechanical efficiency of the compressors. Applied to each stage. "
        "Value must be between 0 (exclusive) and 1 (inclusive). Typical values: 0.93-0.97.",
        title="MECHANICAL_EFFICIENCY",
        gt=0.0,
        le=1.0,
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

    @model_validator(mode="after")
    def validate_mechanical_efficiency_and_legacy_params(self) -> "YamlSimplifiedVariableSpeedCompressorTrain":
        """Validate mutual exclusivity between MECHANICAL_EFFICIENCY and legacy POWER_ADJUSTMENT_* params."""
        has_mechanical_efficiency = self.mechanical_efficiency != 1.0
        has_legacy_constant = self.power_adjustment_constant != 0.0
        has_legacy_factor = self.power_adjustment_factor != 1.0

        # Mutual exclusivity check
        if has_mechanical_efficiency and (has_legacy_constant or has_legacy_factor):
            raise ValueError(
                "MECHANICAL_EFFICIENCY cannot be used together with POWER_ADJUSTMENT_CONSTANT or "
                "POWER_ADJUSTMENT_FACTOR. Use MECHANICAL_EFFICIENCY instead of the deprecated parameters."
            )

        # Deprecation warnings for legacy params
        if has_legacy_constant:
            logger.warning(
                f"POWER_ADJUSTMENT_CONSTANT is deprecated for '{self.name}'. "
                f"Use MECHANICAL_EFFICIENCY instead. See migration guide for conversion."
            )
        if has_legacy_factor:
            logger.warning(
                f"POWER_ADJUSTMENT_FACTOR is deprecated for '{self.name}'. "
                f"Use MECHANICAL_EFFICIENCY (= 1 / POWER_ADJUSTMENT_FACTOR) instead."
            )

        return self

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

                    chart_type = getattr(compressor_chart, "chart_type", None)
                    if chart_type is None:
                        continue

                    if chart_type not in allowed_charts_simplified_trains:
                        raise ValueError(
                            f"{chart_type.value} compressor chart is not supported for {self.type.value}. "
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


class YamlMultipleStreamsStreamIngoing(YamlBase):
    type: Literal["INGOING"]
    name: str
    fluid_model: FluidModelReference = Field(..., description="Reference to a fluid model", title="FLUID_MODEL")


class YamlMultipleStreamsStreamOutgoing(YamlBase):
    type: Literal["OUTGOING"]
    name: str


YamlMultipleStreamsStream = Annotated[
    YamlMultipleStreamsStreamIngoing | YamlMultipleStreamsStreamOutgoing, Field(discriminator="type")
]


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
        description="[DEPRECATED] Constant to adjust power usage in MW. Use SHAFT with MECHANICAL_EFFICIENCY instead.",
        title="POWER_ADJUSTMENT_CONSTANT",
    )
    power_adjustment_factor: float = Field(
        1.0,
        description="[DEPRECATED] Factor to adjust power usage in MW. Use SHAFT with MECHANICAL_EFFICIENCY instead.",
        title="POWER_ADJUSTMENT_FACTOR",
    )
    shaft: ShaftReference | None = Field(
        None,
        description="Reference to a SHAFT model that defines mechanical efficiency for this compressor train. "
        "If not specified, an implicit shaft with mechanical efficiency of 1.0 is used.",
        title="SHAFT",
    )

    def to_dto(self):
        raise NotImplementedError

    @model_validator(mode="after")
    def check_interstage_control_pressure(self):
        count = len(
            [
                stage.interstage_control_pressure
                for stage in self.stages
                if stage.interstage_control_pressure is not None
            ]
        )
        if count > 1:
            raise ValueError("Only one stage can have interstage control pressure defined.")
        return self

    @model_validator(mode="after")
    def validate_shaft_and_legacy_params(self):
        """Validate mutual exclusivity of SHAFT and legacy power adjustment parameters."""
        has_shaft = self.shaft is not None
        has_legacy_factor = self.power_adjustment_factor != 1.0
        has_legacy_constant = self.power_adjustment_constant != 0.0

        if has_shaft and (has_legacy_factor or has_legacy_constant):
            raise ValueError(
                f"Model '{self.name}': Cannot specify both SHAFT and POWER_ADJUSTMENT_FACTOR/POWER_ADJUSTMENT_CONSTANT. "
                "Use SHAFT with MECHANICAL_EFFICIENCY instead of legacy power adjustment parameters."
            )

        if has_legacy_factor or has_legacy_constant:
            logger.warning(
                f"Model '{self.name}': POWER_ADJUSTMENT_FACTOR and POWER_ADJUSTMENT_CONSTANT are deprecated "
                "and will be removed in a future version. Use SHAFT with MECHANICAL_EFFICIENCY instead. "
                "See migration guide: https://equinor.github.io/ecalc/changelog/migration/mechanical-efficiency"
            )

        return self


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
