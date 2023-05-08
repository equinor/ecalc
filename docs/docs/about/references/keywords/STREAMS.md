# STREAMS

[MODELS](MODELS) /
[...] /
[STREAMS](STREAMS.md)

## Description

This keyword can **only** be utilised for a `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES` model type.

`STREAMS` is a list of all in- and out-going streams for the compressor train.

- The same equation of state (EOS) must be used for each INGOING stream fluid models
- OUTGOING fluid models **cannot** be specified.

## Format

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    STREAMS: 
      - NAME: <name of stream 1>
        TYPE: INGOING
        FLUID_MODEL: <reference to fluid model, must be defined in MODELS>
      - NAME: <name of stream 2>
        TYPE: INGOING
        FLUID_MODEL: <reference to fluid model, must be defined in MODELS>
      - ...
      - NAME: <name of stream N>
        TYPE: OUTGOING 
    ...
~~~~~~~~

## Example

~~~~~~~~yaml
MODELS:
  - NAME: compressor_model
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    STREAMS: 
      - NAME: 1_stage_inlet
        TYPE: INGOING
        FLUID_MODEL: fluid_model_1
      - NAME: 3_stage_inlet
        TYPE: INGOING
        FLUID_MODEL: fluid_model_2
      - NAME: 2_stage_outlet
        TYPE: OUTGOING
    ...
~~~~~~~~