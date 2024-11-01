from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated

from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlChartType, YamlModelType


class Units(BaseModel):
    rate: Annotated[Optional[Literal["AM3_PER_HOUR"]], Field(serialization_alias="RATE")] = "AM3_PER_HOUR"
    head: Annotated[Optional[Literal["M", "KJ_PER_KG", "JOULE_PER_KG"]], Field(serialization_alias="HEAD")] = "M"
    efficiency: Annotated[Literal["FRACTION", "PERCENTAGE"], Field(serialization_alias="EFFICIENCY")] = "FRACTION"


class Models(BaseModel):
    models: Annotated[List[Any], Field(serialization_alias="MODELS")]


class Curve(BaseModel):
    # model_config = ConfigDict(extra='allow')
    _min_speed: Annotated[int, Field(1000, init=True)]
    _max_speed: Annotated[int, Field(6000, init=True)]
    _min_rate: Annotated[int, Field(4000, init=True)]
    _max_rate: Annotated[int, Field(7000, init=True)]
    _min_head: Annotated[int, Field(default=6000, init=True)]
    _max_head: Annotated[int, Field(default=9000, init=True)]
    _min_efficiency: Annotated[float, Field(default=0.7, init=True)]
    _max_efficiency: Annotated[float, Field(default=0.8, init=True)]

    speed: Annotated[int, Field(init=False, serialization_alias="SPEED")]
    rate: Annotated[List[int], Field(init=False, serialization_alias="RATE")]
    head: Annotated[List[int], Field(init=False, serialization_alias="HEAD")]
    efficiency: Annotated[List[float], Field(init=False, serialization_alias="EFFICIENCY")]


class Composition(BaseModel):
    water: Annotated[float, Field(ge=0, le=1)] = 0
    nitrogen: Annotated[float, Field(ge=0, le=1)] = 0
    CO2: Annotated[float, Field(ge=0, le=1)] = 0
    methane: Annotated[float, Field(ge=0, le=1)] = 0
    ethane: Annotated[float, Field(ge=0, le=1)] = 0
    propane: Annotated[float, Field(ge=0, le=1)] = 0
    i_butane: Annotated[float, Field(ge=0, le=1)] = 0
    n_butane: Annotated[float, Field(ge=0, le=1)] = 0
    i_pentane: Annotated[float, Field(ge=0, le=1)] = 0
    n_pentane: Annotated[float, Field(ge=0, le=1)] = 0
    n_hexane: Annotated[float, Field(ge=0, le=1)] = 0


class FluidModel(BaseModel):
    name: Annotated[str, Field(serialization_alias="NAME")]
    type: Annotated[str, Field(serialization_alias="TYPE")] = YamlModelType.FLUID.value
    fluid_model_type: Annotated[Literal["PREDEFINED", "COMPOSITION"], Field(serialization_alias="FLUID_MODEL_TYPE")]
    eos_model: Annotated[Literal["SRK", "PR", "GERG_SRK", "GERG_PR"], Field(serialization_alias="EOS_MODEL")]
    gas_type: Annotated[
        Optional[Literal["ULTRA_DRY", "DRY", "MEDIUM", "RICH", "ULTRA_RICH"]], Field(serialization_alias="GAS_TYPE")
    ] = None
    composition: Annotated[Optional[Composition], Field(serialization_alias="COMPOSITION")] = None

    @model_validator(mode="after")
    def check_model_type(self):
        if self.fluid_model_type == "PREDEFINED":
            self.composition = None
            if self.gas_type is None:
                raise ValueError("Gas type must be specified for PREDEFINED fluid model")
        if self.fluid_model_type == "COMPOSITION":
            self.gas_type = None
            if self.composition is None:
                raise ValueError("Composition must be specified for COMPOSITION fluid model")
        return self


class CompressorChart(BaseModel):
    name: Annotated[str, Field(serialization_alias="NAME")]
    type: Annotated[str, Field(serialization_alias="TYPE")] = YamlModelType.COMPRESSOR_CHART.value
    units: Annotated[Units, Field(serialization_alias="UNITS")]


class ChartSingleSpeed(CompressorChart):
    curve: Annotated[Curve, Field(serialization_alias="CURVE")]
    chart_type: Annotated[str, Field(serialization_alias="CHART_TYPE")] = YamlChartType.SINGLE_SPEED.value


class ChartVariableSpeed(CompressorChart):
    curves: List[Curve]
    chart_type: str = YamlChartType.VARIABLE_SPEED.value


class ChartGenericFromInput(CompressorChart):
    polytropic_efficiency: float
    chart_type: str = YamlChartType.GENERIC_FROM_INPUT.value


class ChartGenericDesignPoint(ChartGenericFromInput):
    design_rate: float
    design_head: float
    chart_type: str = YamlChartType.GENERIC_FROM_DESIGN_POINT.value


class Stage(BaseModel):
    inlet_temperature: Annotated[float, Field(ge=10, le=60, serialization_alias="INLET_TEMPERATURE")]
    compressor_chart: Annotated[str, Field(serialization_alias="COMPRESSOR_CHART")]
    pressure_drop_ahead_of_stage: Annotated[
        Optional[float], Field(serialization_alias="PRESSURE_DROP_AHEAD_OF_STAGE")
    ] = None
    control_margin: Annotated[Optional[float], Field(serialization_alias="CONTROL_MARGIN", ge=0)]
    control_margin_unit: Annotated[Optional[str], Field(serialization_alias="CONTROL_MARGIN_UNIT")]


class Stages(BaseModel):
    stages: Annotated[Union[List[Stage], Stage], Field(serialization_alias="STAGES")]


class TrainUnknownStages(BaseModel):
    inlet_temperature: float
    compressor_chart: str
    maximum_pressure_ratio_per_stage: float


class CompressorTrainBase(BaseModel):
    name: Annotated[str, Field(serialization_alias="NAME")]
    fluid_model: Annotated[str, Field(serialization_alias="FLUID_MODEL")]
    pressure_control: Annotated[
        Literal["DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE", "INDIVIDUAL_ASV_PRESSURE", "INDIVIDUAL_ASV_RATE", "COMMON_ASV"],
        Field(serialization_alias="PRESSURE_CONTROL"),
    ]
    power_adjustment_constant: Annotated[Optional[float], Field(serialization_alias="POWER_ADJUSTMENT_CONSTANT")] = None
    maximum_power: Annotated[Optional[float], Field(serialization_alias="MAXIMUM_POWER", ge=0)] = None
    calculate_max_rate: Annotated[Optional[bool], Field(serialization_alias="CALCULATE_MAX_RATE")] = None


class SingleSpeedTrainModel(CompressorTrainBase):
    type: Annotated[str, Field(serialization_alias="TYPE")] = YamlModelType.SINGLE_SPEED_COMPRESSOR_TRAIN.value
    compressor_train: Annotated[Stages, Field(serialization_alias="COMPRESSOR_TRAIN")]
    maximum_discharge_pressure: Annotated[Optional[float], Field(serialization_alias="MAXIMUM_DISCHARGE_PRESSURE")] = (
        None
    )


class VariableSpeedTrainModel(CompressorTrainBase):
    type: Annotated[str, Field(serialization_alias="TYPE")] = YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN.value
    compressor_train: Annotated[Stages, Field(serialization_alias="COMPRESSOR_TRAIN")]
    maximum_discharge_pressure: Annotated[Optional[float], Field(serialization_alias="MAXIMUM_DISCHARGE_PRESSURE")] = (
        None
    )


class SimplifiedVariableSpeedTrainUnknownStagesModel(CompressorTrainBase):
    type: Annotated[str, Field(serialization_alias="TYPE")] = (
        YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN.value
    )
    compressor_train: Annotated[TrainUnknownStages, Field(serialization_alias="COMPRESSOR_TRAIN")]


class SimplifiedVariableSpeedTrainKnownStagesModel(CompressorTrainBase):
    type: Annotated[str, Field(serialization_alias="TYPE")] = (
        YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN.value
    )
    compressor_train: Annotated[Stages, Field(serialization_alias="COMPRESSOR_TRAIN")]
