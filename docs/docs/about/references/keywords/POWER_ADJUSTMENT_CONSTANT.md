# POWER_ADJUSTMENT_CONSTANT

[MODELS](MODELS) / 
[POWER_ADJUSTMENT_CONSTANT](POWER_ADJUSTMENT_CONSTANT)

## Description
Optional constant MW adjustment added to the model. Only added if (electrical) POWER > 0.

## Format

~~~~~yaml
MODELS:
    - NAME: <model name>
      TYPE: <model type>
      ...
      POWER_ADJUSTMENT_CONSTANT: <value in MW>
~~~~~

## Example

~~~~~yaml
MODELS:
  - NAME: simple_compressor
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    ...
    POWER_ADJUSTMENT_CONSTANT: 10 #MW
~~~~~
