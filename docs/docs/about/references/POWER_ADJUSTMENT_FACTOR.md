# POWER_ADJUSTMENT_FACTOR

[MODELS](/about/references/MODELS.md) / 
[POWER_ADJUSTMENT_FACTOR](/about/references/POWER_ADJUSTMENT_FACTOR.md)

:::warning Deprecated
This parameter is deprecated and will be removed in a future version. Use [SHAFT](/about/references/SHAFT.md) with [MECHANICAL_EFFICIENCY](/about/references/MECHANICAL_EFFICIENCY.md) instead for a physically meaningful way to model mechanical losses.
:::

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

**Deprecated usage:**
~~~~~yaml
MODELS:
  - NAME: simple_compressor
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    ...
    POWER_ADJUSTMENT_FACTOR: 1.2 
~~~~~

**Recommended migration:** See the [Mechanical Efficiency Migration Guide](/about/migration_guides/mechanical_efficiency.md).
