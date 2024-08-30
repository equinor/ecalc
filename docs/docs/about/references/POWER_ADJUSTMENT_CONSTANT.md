# POWER_ADJUSTMENT_CONSTANT

[MODELS](/about/references/MODELS.md) / 
[POWER_ADJUSTMENT_CONSTANT](/about/references/POWER_ADJUSTMENT_CONSTANT.md)

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
