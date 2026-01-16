# POWER_ADJUSTMENT_CONSTANT

[MODELS](/about/references/MODELS.md) / 
[POWER_ADJUSTMENT_CONSTANT](/about/references/POWER_ADJUSTMENT_CONSTANT.md)

:::warning Deprecated
This parameter is deprecated and will be removed in a future version. Use [MECHANICAL_EFFICIENCY](/about/references/MECHANICAL_EFFICIENCY.md) instead for a physically meaningful way to model mechanical losses.
:::

## Description
Optional constant MW adjustment added to the model. Only added if (electrical) POWER > 0. Can be used in combination with [POWER_ADJUSTMENT_FACTOR](/about/references/POWER_ADJUSTMENT_FACTOR.md).

## Format

~~~~~yaml
MODELS:
    - NAME: <model name>
      TYPE: <model type>
      ...
      POWER_ADJUSTMENT_CONSTANT: <value in MW>
~~~~~

## Example

**Deprecated usage:**
~~~~~yaml
MODELS:
  - NAME: simple_compressor
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    ...
    POWER_ADJUSTMENT_CONSTANT: 10 #MW
~~~~~

**Recommended migration:** See the [Mechanical Efficiency Migration Guide](/about/migration_guides/mechanical_efficiency.md).