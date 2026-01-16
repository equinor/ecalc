---
title: Mechanical Efficiency Migration
description: Migrating from POWER_ADJUSTMENT_FACTOR to SHAFT with MECHANICAL_EFFICIENCY
sidebar_position: -16
---

# Migrating to SHAFT with MECHANICAL_EFFICIENCY

This guide explains how to migrate from the deprecated `POWER_ADJUSTMENT_FACTOR` and `POWER_ADJUSTMENT_CONSTANT` parameters to the new `SHAFT` model with `MECHANICAL_EFFICIENCY`.

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

### Common-Shaft Trains

For `VARIABLE_SPEED_COMPRESSOR_TRAIN`, `SINGLE_SPEED_COMPRESSOR_TRAIN`, and `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`:

**Before:**
```yaml
- NAME: export_compressor
  TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
  POWER_ADJUSTMENT_FACTOR: 1.05
  ...
```

**After:**
```yaml
- NAME: export_shaft
  TYPE: SHAFT
  MECHANICAL_EFFICIENCY: 0.952

- NAME: export_compressor
  TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
  SHAFT: export_shaft
  ...
```

:::note
Each `SHAFT` can only be used by one compressor train. Create separate shaft models if you have multiple trains.
:::

### Simplified Trains

For `SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN`, set `MECHANICAL_EFFICIENCY` directly on the train:

**Before:**
```yaml
- NAME: simple_train
  TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
  POWER_ADJUSTMENT_FACTOR: 1.08
  ...
```

**After:**
```yaml
- NAME: simple_train
  TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
  MECHANICAL_EFFICIENCY: 0.926
  ...
```

## Troubleshooting

**Cannot specify both SHAFT and POWER_ADJUSTMENT_FACTOR**: Remove the legacy parameter when using `SHAFT` or `MECHANICAL_EFFICIENCY`.

**SHAFT is referenced by multiple trains**: Each shaft can only be used by one train. Create separate shaft models.

## Further Reading

- [SHAFT Reference](/about/references/SHAFT.md)
- [MECHANICAL_EFFICIENCY Reference](/about/references/MECHANICAL_EFFICIENCY.md)
