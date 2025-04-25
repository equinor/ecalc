# POWER_ADJUSTMENT_FACTOR

[MODELS](/about/references/MODELS.md) / 
[POWER_ADJUSTMENT_FACTOR](/about/references/POWER_ADJUSTMENT_FACTOR.md)

## Description
Optional factor adjusting the power in the model. The power is multiplied by this factor. Can be used in combination with [POWER_ADJUSTMENT_CONSTANT](/about/references/POWER_ADJUSTMENT_CONSTANT.md).

## Format

~~~~~yaml
MODELS:
    - NAME: <model name>
      TYPE: <model type>
      ...
      POWER_ADJUSTMENT_FACTOR: <value>
~~~~~

## Example

~~~~~yaml
MODELS:
  - NAME: simple_compressor
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    ...
    POWER_ADJUSTMENT_FACTOR: 1.2 
~~~~~

~~~~~yaml
MODELS:
  - NAME: simple_compressor
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    ...
    POWER_ADJUSTMENT_CONSTANT: 10 #MW
    POWER_ADJUSTMENT_FACTOR: 1.2 
~~~~~
