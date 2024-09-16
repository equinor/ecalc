# PRESSURE_CONTROL

## Description
The `PRESSURE_CONTROL` dictates how the compressor will be controlled when running on a fixed speed. The available
methods for pressure control are as follows:

- DOWNSTREAM_CHOKE (default)
- UPSTREAM_CHOKE
- INDIVIDUAL_ASV_PRESSURE
- INDIVIDUAL_ASV_RATE
- COMMON_ASV

`PRESSURE_CONTROL` is in use for the following types of compressor trains:
- [`Single speed compressor train model`](/about/modelling/setup/models/compressor_modelling/compressor_models_types/single_speed_compressor_train_model.md)
- [`Variable speed compressor train model`](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model.md)
- [`Variable speed compressor train model with multiple streams and pressures`](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures.md)

Further description on how each pressure control method works can be found in [Fixed speed pressure control](/about/modelling/setup/models/compressor_modelling/fixed_speed_pressure_control/index.md)

## Format

~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: <compressor model type>
    ...
    PRESSURE_CONTROL: <method for pressure control, DOWNSTREAM_CHOKE (default), UPSTREAM_CHOKE, , INDIVIDUAL_ASV_PRESSURE, INDIVIDUAL_ASV_RATE or COMMON_ASV>
~~~~

## Example

~~~~yaml
MODELS:
  - NAME: variable_compressor
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
    ...
    PRESSURE_CONTROL: INDIVIDUAL_ASV_PRESSURE
~~~~
