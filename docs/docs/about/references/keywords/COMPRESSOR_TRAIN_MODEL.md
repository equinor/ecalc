# COMPRESSOR_TRAIN_MODEL

[INSTALLATIONS](INSTALLATIONS) /
[...] / 
[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL) /
[COMPRESSOR_TRAIN_MODEL](COMPRESSOR_TRAIN_MODEL)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | `ENERGY_USAGE_MODEL`      | None                               |

## Description
Reference to an compressor train model defined in [FACILITY_INPUTS](FACILITY_INPUTS) or 
[MODELS](MODELS) used for [ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL) 
TYPE [VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES](ENERGY_USAGE_MODEL#variable_speed_compressor_train_multiple_streams_and_pressures-energy-usage-model).

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

