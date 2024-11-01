from typing import Dict, Generic, List, Optional, TypeVar, Union, cast

from models_test_setup import (
    ChartSingleSpeed,
    ChartVariableSpeed,
    Curve,
    FluidModel,
    SimplifiedVariableSpeedTrainKnownStagesModel,
    SimplifiedVariableSpeedTrainUnknownStagesModel,
    SingleSpeedTrainModel,
    Stage,
    VariableSpeedTrainModel,
)
from polyfactory import Require
from polyfactory.decorators import post_generated
from polyfactory.factories.pydantic_factory import ModelFactory

from libecalc.dto import GenericChartFromDesignPoint, GenericChartFromInput
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator


def remove_null_none_empty(ob):
    cleaned = {}
    for k, v in ob.items():
        if isinstance(v, dict):
            x = remove_null_none_empty(v)
            if len(x.keys()) > 0:
                cleaned[k] = x

        elif isinstance(v, list):
            p = []
            for c in v:
                if isinstance(c, dict):
                    x = remove_null_none_empty(c)
                    if len(x.keys()) > 0:
                        p.append(x)
                elif c is not None and c != "":
                    p.append(c)
            cleaned[k] = p
        elif v is not None and v != "":
            cleaned[k] = v
    return cleaned


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


class CurveFactory(ModelFactory[Curve]):
    nr_samples = 4
    __use_defaults__ = True
    __randomize_collection_length__ = True
    __min_collection_length__ = nr_samples
    __max_collection_length__ = nr_samples

    @post_generated
    @classmethod
    def speed(cls, _min_speed: int, _max_speed: int) -> int:
        speed = cls.__random__.randint(a=_min_speed, b=_max_speed)
        return speed

    @post_generated
    @classmethod
    def rate(cls, _min_rate: int, _max_rate: int) -> List[int]:
        rate = []
        for _i in range(cls.nr_samples):
            rate_sample = cls.__random__.randint(a=_min_rate, b=_max_rate)
            rate.append(rate_sample)
        return sorted(rate)

    @post_generated
    @classmethod
    def head(cls, _min_head: int, _max_head: int) -> List[int]:
        head = []
        for _i in range(cls.nr_samples):
            head_sample = cls.__random__.randint(a=_min_head, b=_max_head)
            head.append(head_sample)
        return sorted(head, reverse=True)

    @post_generated
    @classmethod
    def efficiency(cls, _min_efficiency: float, _max_efficiency: float) -> List[float]:
        efficiency = []
        for _i in range(cls.nr_samples):
            efficiency_sample = cls.__random__.uniform(a=_min_efficiency, b=_max_efficiency)
            efficiency.append(efficiency_sample)
        return efficiency


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
