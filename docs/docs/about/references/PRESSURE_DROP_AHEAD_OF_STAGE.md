# PRESSURE_DROP_AHEAD_OF_STAGE

[MODELS](/about/references/MODELS.md) /
[...] /
[STAGES](/about/references/STAGES.md) /
[PRESSURE_DROP_AHEAD_OF_STAGE](/about/references/PRESSURE_DROP_AHEAD_OF_STAGE.md)

## Description
This is a keyword used in [COMPRESSOR MODELLING](/about/modelling/setup/models/compressor_modelling/compressor_models_types/index.md)  when defining the individual stages of a compressor train.
It is an optional input parameter. If defined, the inlet pressure of the stage will be reduced with that value before the actual compression starts.

As of now, this is can only be given as a single value. Time-series are not accepted here.

## Format

~~~~~yaml
MODELS:
  - NAME: <model name>
    ...
    COMPRESSOR_TRAIN:
      STAGES:
        - PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
    ...
~~~~~

## Example

~~~~~yaml
MODELS:
  - NAME: compressor_train
    ...
    COMPRESSOR_TRAIN:
      STAGES:
        - PRESSURE_DROP_AHEAD_OF_STAGE: 2.2 #bar
    ...
~~~~~
