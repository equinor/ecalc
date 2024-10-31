from typing import Dict, Generic, List, Literal, Optional, TypeVar, Union, cast

from polyfactory import Require
from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated

from libecalc.dto import GenericChartFromDesignPoint, GenericChartFromInput
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlChartType, YamlModelType


class OverridableStreamConfigurationService(ConfigurationService):
    def __init__(self, stream: ResourceStream, overrides: Optional[Dict] = None):
        self._overrides = overrides
        self._stream = stream

    def get_configuration(self) -> YamlValidator:
        main_yaml_model = YamlConfiguration.Builder.get_yaml_reader(ReaderType.PYYAML).read(
            main_yaml=self._stream,
            enable_include=True,
        )

        if self._overrides is not None:
            main_yaml_model._internal_datamodel.update(self._overrides)
        return cast(YamlValidator, main_yaml_model)


class Units(BaseModel):
    rate: Optional[str]
    head: Optional[str]
    efficiency: Literal["FRACTION", "PERCENTAGE"]


class Curve(BaseModel):
    speed: List[Annotated[float, Field(ge=0)]]
    rate: List[Annotated[float, Field(ge=0)]]
    head: List[Annotated[float, Field(ge=0)]]
    efficiency: List[Annotated[float, Field(ge=0)]]


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
    name: str
    type: str = YamlModelType.FLUID.value
    fluid_model_type: Literal["PREDEFINED", "COMPOSITION"]
    eos_model: Literal["SRK", "PR", "GERG_SRK", "GERG_PR"]
    gas_type: Optional[Literal["ULTRA_DRY", "DRY", "MEDIUM", "RICH", "ULTRA_RICH"]] = None
    composition: Optional[Composition] = None

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
    name: str
    type: str = YamlModelType.COMPRESSOR_CHART.value
    units: Units


class ChartSingleSpeed(CompressorChart):
    curve: Curve
    chart_type: str = YamlChartType.SINGLE_SPEED.value


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
    inlet_temperature: float
    compressor_chart: str
    pressure_drop_ahead_of_stage: Optional[float] = None
    control_margin: Optional[float] = None
    control_margin_unit: Optional[str] = None


class TrainUnknownStages(BaseModel):
    inlet_temperature: float
    compressor_chart: str
    maximum_pressure_ratio_per_stage: float


class CompressorTrainBase(BaseModel):
    name: str
    fluid_model: FluidModel
    pressure_control: Literal[
        "DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE", "INDIVIDUAL_ASV_PRESSURE", "INDIVIDUAL_ASV_RATE", "COMMON_ASV"
    ]
    power_adjustment_constant: Optional[float] = None
    maximum_power: Optional[float] = None
    calculate_max_rate: Optional[bool] = None


class SingleSpeedTrainModel(CompressorTrainBase):
    type: str = YamlModelType.SINGLE_SPEED_COMPRESSOR_TRAIN.value
    compressor_train: List[Stage]
    maximum_discharge_pressure: Optional[float] = None


class VariableSpeedTrainModel(CompressorTrainBase):
    type: str = YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN.value
    compressor_train: List[Stage]
    maximum_discharge_pressure: Optional[float] = None


class SimplifiedVariableSpeedTrainUnknownStagesModel(CompressorTrainBase):
    type: str = YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN.value
    compressor_train: TrainUnknownStages


class SimplifiedVariableSpeedTrainKnownStagesModel(CompressorTrainBase):
    type: str = YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN.value
    compressor_train: List[Stage]


class FluidModelFactory(ModelFactory[FluidModel]):
    __use_defaults__ = True

    # Required parameters when creating instance of fluid model:
    fluid_model_type = Require()  # PREDEFINED or COMPOSITION
    eos_model = Require()  # SRK, PR, GERG_SRK or GERG_PR


TChart = TypeVar(
    "TChart", bound=Union[ChartSingleSpeed, ChartVariableSpeed, GenericChartFromInput, GenericChartFromDesignPoint]
)


class CustomChartFactory(Generic[TChart], ModelFactory[TChart]):
    __is_base_factory__ = True
    __use_defaults__ = True


class SingleSpeedChartFactory(CustomChartFactory[ChartSingleSpeed]): ...


class VariableSpeedChartFactory(CustomChartFactory[ChartVariableSpeed]): ...


class GenericInputChartFactory(CustomChartFactory[GenericChartFromInput]): ...


class GenericInputDesignPointFactory(CustomChartFactory[GenericChartFromDesignPoint]): ...


TCompTrain = TypeVar(
    "TCompTrain",
    bound=Union[
        SingleSpeedTrainModel,
        VariableSpeedTrainModel,
        SimplifiedVariableSpeedTrainUnknownStagesModel,
        SimplifiedVariableSpeedTrainKnownStagesModel,
    ],
)


class CustomTrainFactory(Generic[TCompTrain], ModelFactory[TCompTrain]):
    __is_base_factory__ = True
    __use_defaults__ = True

    # pressure_control = Require()
    fluid_model = Require()
    compressor_train = Require()


class SingleSpeedTrainFactory(CustomTrainFactory[SingleSpeedTrainModel]): ...


class VariableSpeedTrainFactory(CustomTrainFactory[VariableSpeedTrainModel]): ...


class SimplifiedVariableSpeedTrainKnownStagesFactory(
    CustomTrainFactory[SimplifiedVariableSpeedTrainUnknownStagesModel]
): ...


class SimplifiedVariableSpeedTrainUnknownStagesFactory(
    CustomTrainFactory[SimplifiedVariableSpeedTrainUnknownStagesModel]
): ...


class StageFactory(ModelFactory[Stage]):
    __use_defaults__ = True
    compressor_chart = Require()


def test_single_speed_compressor_train() -> None:
    chart_instance = SingleSpeedChartFactory.build()
    stage_instance = StageFactory.build(compressor_chart=chart_instance.name)

    compressor_instance = SingleSpeedTrainFactory.build(
        compressor_chart=chart_instance.name,
        compressor_train=[stage_instance],
        fluid_model=FluidModelFactory.build(fluid_model_type="PREDEFINED", gas_type="DRY", eos_model="SRK"),
    )
    assert isinstance(compressor_instance, CompressorTrainBase)


yaml_fluid_model = """
  - NAME: fluid_model
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    EOS_MODEL: SRK
    GAS_TYPE: MEDIUM
"""

yaml_chart_single_speed = """
  - NAME: single_speed_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: SINGLE_SPEED
    UNITS:
      RATE: AM3_PER_HOUR
      HEAD: M
      EFFICIENCY: FRACTION
    CURVE:
        SPEED: 7500
        RATE: [3000, 3500, 4000, 4500]
        HEAD: [8400, 8000, 7400, 6000]
        EFFICIENCY: [0.72, 0.75, 0.74, 0.70]
"""

yaml_chart_variable_speed = """
  - NAME: variable_speed_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: VARIABLE_SPEED
    UNITS:
      RATE: AM3_PER_HOUR
      HEAD: M
      EFFICIENCY: FRACTION
    CURVES:
      - SPEED: 7500
        RATE: [3000, 3500, 4000, 4500]
        HEAD: [8400, 8000, 7363, 6000]
        EFFICIENCY: [0.72, 0.75, 0.74, 0.70]
      - SPEED: 9900
        RATE: [3700, 4500, 5000, 5500, 6000]
        HEAD: [13900, 13200, 12400, 11300, 10000]
        EFFICIENCY: [0.72, 0.75, 0.748, 0.73, 0.70]
      - SPEED: 10800
        RATE: [4000, 4500, 5000, 5500, 6000, 6400]
        HEAD: [16500, 16000, 15500, 14600, 13500, 12000]
        EFFICIENCY: [0.72, 0.73, 0.74, 0.74, 0.72, 0.70]
"""


yaml_chart_generic_from_input = """
  - NAME: generic_from_input_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: GENERIC_FROM_INPUT
    POLYTROPIC_EFFICIENCY: 0.75
    UNITS:
      EFFICIENCY: FRACTION
"""


yaml_simplified_train_wrong_chart = f"""
MODELS:
  {yaml_fluid_model}
  {yaml_chart_single_speed}
  - NAME: simplified_compressor_train
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: fluid_model
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: single_speed_compressor_chart
"""

yaml_simplified_train_with_control_margin_and_pressure_drop = f"""
MODELS:
  {yaml_fluid_model}
  {yaml_chart_generic_from_input}
  - NAME: simplified_compressor_train
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: fluid_model
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          CONTROL_MARGIN: 10
          CONTROL_MARGIN_UNIT: PERCENTAGE
          PRESSURE_DROP_AHEAD_OF_STAGE: 2
          COMPRESSOR_CHART: generic_from_input_compressor_chart
    """

yaml_single_speed_train_without_control_margin = f"""
MODELS:
  {yaml_fluid_model}
  {yaml_chart_single_speed}
  - NAME: single_speed_compressor_train
    TYPE: SINGLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: fluid_model
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: single_speed_compressor_chart
          PRESSURE_DROP_AHEAD_OF_STAGE: 2
"""

yaml_variable_speed_train_without_control_margin = f"""
MODELS:
  {yaml_fluid_model}
  {yaml_chart_variable_speed}
  - NAME: variable_speed_compressor_train
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: fluid_model
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: variable_speed_compressor_chart
          PRESSURE_DROP_AHEAD_OF_STAGE: 2
    """
