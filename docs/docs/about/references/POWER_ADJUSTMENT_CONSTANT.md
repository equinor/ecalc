# POWER_ADJUSTMENT_CONSTANT

[MODELS](/about/references/MODELS.md) / 
[POWER_ADJUSTMENT_CONSTANT](/about/references/POWER_ADJUSTMENT_CONSTANT.md)

## Description {/* #description */}
Optional constant MW adjustment added to the model. Only added if (electrical) POWER > 0. Can be used in combination with [POWER_ADJUSTMENT_FACTOR](/about/references/POWER_ADJUSTMENT_FACTOR.md).

## Format {/* #format */}

~~~~~yaml
MODELS:
    - NAME: <model name>
      TYPE: <model type>
      ...
      POWER_ADJUSTMENT_CONSTANT: <value in MW>
~~~~~

## Example {/* #example */}

~~~~~yaml
MODELS:
  - NAME: simple_compressor
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    ...
    POWER_ADJUSTMENT_CONSTANT: 10 #MW
~~~~~

~~~~~yaml
MODELS:
  - NAME: simple_compressor
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    ...
    POWER_ADJUSTMENT_CONSTANT: 10 #MW
    POWER_ADJUSTMENT_FACTOR: 1.2 
~~~~~