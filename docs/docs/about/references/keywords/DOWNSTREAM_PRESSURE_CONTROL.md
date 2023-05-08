# DOWNSTREAM_PRESSURE_CONTROL

[MODELS](MODELS) /
[...] /
[INTERSTAGE_CONTROL_PRESSURE](INTERSTAGE_CONTROL_PRESSURE)
/ [DOWNSTREAM_PRESSURE_CONTROL](DOWNSTREAM_PRESSURE_CONTROL)

## Description
This keyword is used only for `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES` type. It is used within the [INTERSTAGE_CONTROL_PRESSURE](INTERSTAGE_CONTROL_PRESSURE) keyword.

The pressure control method downstream (after) the interstage pressure is specified in this keyword.
For more explanation see [Variable speed compressor train model with multiple streams and pressures](../../modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures).

## Format

~~~~yaml
MODELS:
  - NAME: <compressor model name>
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    ...
    STAGES:
        ...
        INTERSTAGE_CONTROL_PRESSURE:
            DOWNSTREAM_PRESSURE_CONTROL: <DOWNSTREAM_CHOKE / UPSTREAM_CHOKE / INDIVIDUAL_ASV_RATE> 
            ...
~~~~

## Example

~~~~yaml
MODELS:
  - NAME: compressor_model
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    ...
    STAGES:
        ...
        INTERSTAGE_CONTROL_PRESSURE:
            UPSTREAM_PRESSURE_CONTROL: UPSTREAM_CHOKE
            DOWNSTREAM_PRESSURE_CONTROL: INDIVIDUAL_ASV_RATE
~~~~
