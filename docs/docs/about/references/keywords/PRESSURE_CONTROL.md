# PRESSURE_CONTROL

## Description
`PRESSURE_CONTROL` is required when a compressor model is defined. This dictates how the compressor will be controlled, the method for pressure control are as follows:

- DOWNSTREAM_CHOKE (default)
- UPSTREAM_CHOKE
- INDIVIDUAL_ASV_PRESSURE
- INDIVIDUAL_ASV_RATE
- COMMON_ASV
- NONE

Further description on how each pressure control method works can be found in [COMPRESSOR MODELLING](../../modelling/setup/models/compressor_modelling/compressor_models_types/)

## Format

~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: <compressor model type>
    ...
    PRESSURE_CONTROL: <method for pressure control, DOWNSTREAM_CHOKE (default), UPSTREAM_CHOKE, , INDIVIDUAL_ASV_PRESSURE, INDIVIDUAL_ASV_RATE, COMMON_ASV or NONE>
~~~~

## Example

~~~~yaml
MODELS:
  - NAME: variable_compressor
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
    ...
    PRESSURE_CONTROL: INDIVIDUAL_ASV_PRESSURE
~~~~
