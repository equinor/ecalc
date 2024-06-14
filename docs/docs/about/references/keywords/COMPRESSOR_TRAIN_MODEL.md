# COMPRESSOR_TRAIN_MODEL

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) /
[...] / 
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) /
[COMPRESSOR_TRAIN_MODEL](/about/references/keywords/COMPRESSOR_TRAIN_MODEL.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | `ENERGY_USAGE_MODEL`      | None                               |

## Description
Reference to a compressor train model defined in [FACILITY_INPUTS](/about/references/keywords/FACILITY_INPUTS.md) or 
[MODELS](/about/references/keywords/MODELS.md) used for [ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) 
TYPE [VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures.md).

## Format
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
  COMPRESSOR_TRAIN_MODEL: <reference to compressor train model in facility inputs or models of compressor type>
~~~~~~~~

## Example
~~~~~~~~yaml
MODELS:
  - NAME: advanced_compressor_train
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    STREAMS:
      -
      -

...

        ENERGY_USAGE_MODEL:
          TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
          COMPRESSOR_TRAIN_MODEL: advanced_compressor_train
~~~~~~~~

