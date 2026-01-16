---
title: Mechanical Efficiency Migration
description: Migrating from POWER_ADJUSTMENT_FACTOR to MECHANICAL_EFFICIENCY
sidebar_position: -16
---

# Migrating to MECHANICAL_EFFICIENCY

This guide explains how to migrate from the deprecated `POWER_ADJUSTMENT_FACTOR` and `POWER_ADJUSTMENT_CONSTANT` parameters to the new `MECHANICAL_EFFICIENCY` parameter.

## Why Migrate?

The legacy power adjustment parameters were empirical corrections without clear physical meaning. The new approach provides:

- **Physical clarity**: Mechanical efficiency represents real-world losses in bearings, gearboxes, and seals
- **Better documentation**: Efficiency values can be traced to equipment specifications
- **Future compatibility**: Legacy parameters will be removed in a future version

## Conversion Formula

$$
\eta_{mechanical} = \frac{1}{\text{POWER\_ADJUSTMENT\_FACTOR}}
$$

For example: `POWER_ADJUSTMENT_FACTOR: 1.05` → `MECHANICAL_EFFICIENCY: 0.952`

:::note
`POWER_ADJUSTMENT_CONSTANT` has no direct equivalent. If you used a constant offset, consult the eCalc team.
:::

## Migration Examples

### All Compressor Train Types

For all compressor train types (`VARIABLE_SPEED_COMPRESSOR_TRAIN`, `SINGLE_SPEED_COMPRESSOR_TRAIN`, `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`, and `SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN`), set `MECHANICAL_EFFICIENCY` directly on the train model:

**Before:**
```yaml
MODELS:
  - NAME: export_compressor
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
    POWER_ADJUSTMENT_FACTOR: 1.05
    FLUID_MODEL: medium_gas
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: compressor_chart_ref
```

**After:**
```yaml
MODELS:
  - NAME: export_compressor
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
    MECHANICAL_EFFICIENCY: 0.952  # = 1/1.05, accounts for 5% mechanical losses
    FLUID_MODEL: medium_gas
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: compressor_chart_ref
```

### Simplified Trains

The same pattern applies to `SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN`:

**Before:**
```yaml
MODELS:
  - NAME: simple_train
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    POWER_ADJUSTMENT_FACTOR: 1.08
    FLUID_MODEL: medium_gas
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: generic_chart
```

**After:**
```yaml
MODELS:
  - NAME: simple_train
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    MECHANICAL_EFFICIENCY: 0.926  # = 1/1.08
    FLUID_MODEL: medium_gas
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: generic_chart
```

## Troubleshooting

**Cannot specify both MECHANICAL_EFFICIENCY and POWER_ADJUSTMENT_FACTOR**: Remove the legacy parameter when using `MECHANICAL_EFFICIENCY`. The two approaches are mutually exclusive.

**MECHANICAL_EFFICIENCY must be in range (0, 1]**: Ensure your value is greater than 0 and at most 1.0. Use the conversion formula above if migrating from `POWER_ADJUSTMENT_FACTOR`.

## Further Reading

- [MECHANICAL_EFFICIENCY Reference](/about/references/MECHANICAL_EFFICIENCY.md)
