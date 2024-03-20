# MAXIMUM_POWER

[MODELS](/about/references/keywords/MODELS.md) / 
[MAXIMUM_POWER](/about/references/keywords/MAXIMUM_POWER.md)

## Description

`MAXIMUM_POWER` is an optional constant giving the maximum power (MW) that the compressor train can use.
## Functionality

 It is an optional setting and supported for compressor train models [SINGLE_SPEED_COMPRESSOR_TRAIN](/about/modelling/setup/models/compressor_modelling/compressor_models_types/single_speed_compressor_train_model.md), [SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN](/about/modelling/setup/models/compressor_modelling/compressor_models_types/simplified_variable_speed_compressor_train_model.md), [VARIABLE_SPEED_COMPRESSOR_TRAIN](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model.md), [VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures.md).

## Format

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: <reference to fluid model, must be defined in [MODELS]>
    COMPRESSOR_TRAIN:
    POWER_ADJUSTMENT_CONSTANT: <Optional constant MW adjustment added to the model>
    MAXIMUM_POWER: <Optional constant MW maximum power the compressor train can require>
    CALCULATE_MAX_RATE: <Optional. compressor train max standard rate [Sm3/day] in result if set to true. Default false. Use with caution. This will increase runtime significantly. >
        ...
~~~~~~~~
