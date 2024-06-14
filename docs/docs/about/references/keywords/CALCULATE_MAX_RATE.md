# CALCULATE_MAX_RATE

[MODELS](/about/references/keywords/MODELS.md) /
[CALCULATE_MAX_RATE](/about/references/keywords/CALCULATE_MAX_RATE.md)

## Description

The keyword [CALCULATE_MAX_RATE](CALCULATE_MAX_RATE) is optional with default value `False`. When set to `True`, the
maximum standard rate the compressor train model can handle, based on the input suction and discharge pressures, will
be calculated and reported in the results. This will be done for all dates according to the requested output frequency.

Calculation of maximum standard rate is supported for compressor train models of type:
- [SINGLE_SPEED_COMPRESSOR_TRAIN](/about/modelling/setup/models/compressor_modelling/compressor_models_types/single_speed_compressor_train_model.md)
- [SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN](/about/modelling/setup/models/compressor_modelling/compressor_models_types/simplified_variable_speed_compressor_train_model.md)
- [VARIABLE_SPEED_COMPRESSOR_TRAIN](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model.md)
- [VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures.md).


:::warning Warning
The CALCULATE_MAX_RATE keyword will in most cases add significantly to the run time of the model.
Only use when needed!
:::

## Format

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: <reference to fluid model, must be defined in [MODELS]>
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
          COMPRESSOR_CHART: <reference to compressor chart model for first stage, must be defined in MODELS or FACILITY_INPUTS>
        - ... and so forth for each stage in the train
    CALCULATE_MAX_RATE: <Optional. compressor train max standard rate [Sm3/day] in result if set to true. Default false. Use with caution. This will increase runtime significantly. >
        ...
~~~~~~~~

## Example

~~~~~~~~yaml
MODELS:
  - NAME: simplified_compressor_model
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: fluid_model_1
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: predefined_variable_speed_compressor_chart
    CALCULATE_MAX_RATE: True
~~~~~~~~

