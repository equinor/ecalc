import pytest


@pytest.fixture
def yaml_fluid_model():
    return """
  - NAME: fluid_model
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    EOS_MODEL: SRK
    GAS_TYPE: MEDIUM
"""


@pytest.fixture
def yaml_chart_single_speed():
    return """
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


@pytest.fixture
def yaml_chart_variable_speed():
    return """
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


@pytest.fixture
def yaml_chart_generic_from_input():
    return """
  - NAME: generic_from_input_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: GENERIC_FROM_INPUT
    POLYTROPIC_EFFICIENCY: 0.75
    UNITS:
      EFFICIENCY: FRACTION
"""


@pytest.fixture
def yaml_simplified_train_wrong_chart(yaml_fluid_model, yaml_chart_single_speed):
    return f"""
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


@pytest.fixture
def yaml_simplified_train_with_control_margin_and_pressure_drop(yaml_fluid_model, yaml_chart_generic_from_input):
    return f"""
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


@pytest.fixture
def yaml_single_speed_train_without_control_margin(yaml_fluid_model, yaml_chart_single_speed):
    return f"""
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


@pytest.fixture
def yaml_variable_speed_train_without_control_margin(yaml_fluid_model, yaml_chart_variable_speed):
    return f"""
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
