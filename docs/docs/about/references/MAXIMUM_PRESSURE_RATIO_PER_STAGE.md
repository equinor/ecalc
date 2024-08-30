# MAXIMUM_PRESSURE_RATIO_PER_STAGE

[MODELS](/about/references/MODELS.md) / 
[MAXIMUM_PRESSURE_RATIO_PER_STAGE](/about/references/MAXIMUM_PRESSURE_RATIO_PER_STAGE.md)

## Description

`MAXIMUM_PRESSURE_RATIO_PER_STAGE` is used in the process of determining (at run time) the number of compressors 
in a [SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN](/about/modelling/setup/models/compressor_modelling/compressor_models_types/simplified_variable_speed_compressor_train_model.md) 
with unknown stages. The number of compressors is set such that there are just enough compressors to ensure no pressure ratios are above the given 
`MAXIMUM_PRESSURE_RATIO_PER_STAGE`.

## Functionality

This is an optional setting and is **only** supported for [SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN](/about/modelling/setup/models/compressor_modelling/compressor_models_types/simplified_variable_speed_compressor_train_model.md) with unknown stages, i.e. if `STAGES` are not specified.


## Format

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: <reference to fluid model, must be defined in [MODELS]>
    COMPRESSOR_TRAIN:
      MAXIMUM_PRESSURE_RATIO_PER_STAGE: <maximum pressure ratio per stage>
      COMPRESSOR_CHART: <reference to compressor chart model used for all stages, must be defined in [MODELS] or [FACILITY_INPUTS]>
      INLET_TEMPERATURE: <inlet temperature for all stages>
    POWER_ADJUSTMENT_CONSTANT: <Optional constant MW adjustment added to the model>
    ...
~~~~~~~~

## Example

~~~~~~~~yaml
MODELS:
  - NAME: simplified_compressor_train_model
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: some_fluid_model
    COMPRESSOR_TRAIN:
      MAXIMUM_PRESSURE_RATIO_PER_STAGE: 3.5
      COMPRESSOR_CHART: some_compressor_chart
      INLET_TEMPERATURE: 30
    ...
~~~~~~~~