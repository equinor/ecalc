# FLUID_MODEL

## Description

This keyword is necessary when defining a compressor model. It relates to a defined fluid model in the `MODELS` section. How a fluid model is defined is described in further detail in [FLUID MODEL](/about/modelling/setup/models/fluid_model.md).

## Format

~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: <compressor model type>
    FLUID_MODEL: <reference to fluid model, must be defined in MODELS>
    ...
~~~~

## Example

~~~~yaml
MODELS:
  - NAME: fluid_model
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    EOS_MODEL: SRK
    GAS_TYPE: MEDIUM

  - NAME: single_speed_compressor
    TYPE: SINGLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: fluid_model
    ...
~~~~
