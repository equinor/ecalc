---
title: Variable speed compressor train multiple streams and pressures
sidebar_position: 3
description: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES Energy Usage Model
---

# VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES energy usage model

This energy usage model allows the compressor train model type 
[Variable speed compressor train model with multiple streams and pressures](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures.md).

## Format

~~~~~~~~yaml
NAME: <Reference name>
TYPE: COMPRESSOR
ENERGY_USAGE_MODEL:
  TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
  CONDITION: <condition expression>
  COMPRESSOR_TRAIN_MODEL: <reference a Variable speed compressor train model with multiple streams and pressures model>
  RATE_PER_STREAM:
    - <Expression for stream 1>
    - <Expression for stream 2>
    - ...
    - <Expression for stream N>
  SUCTION_PRESSURE: <suction pressure expression>
  DISCHARGE_PRESSURE: <discharge pressure expression>
  INTERSTAGE_CONTROL_PRESSURE: <interstage control pressure expression>
~~~~~~~~

:::warning Deprecated Parameters
The `POWER_ADJUSTMENT_CONSTANT` parameter is deprecated. Use `MECHANICAL_EFFICIENCY` on the train model definition instead.
:::

The number of elements in [RATE_PER_STREAM](/about/references/RATE_PER_STREAM.md) must correspond to the number of streams defined for the model referenced in
[COMPRESSOR_TRAIN_MODEL](/about/references/COMPRESSOR_TRAIN_MODEL.md).

[INTERSTAGE_CONTROL_PRESSURE](/about/references/INTERSTAGE_CONTROL_PRESSURE.md) is required if the model referenced in [COMPRESSOR_TRAIN_MODEL](/about/references/COMPRESSOR_TRAIN_MODEL.md) has has an
interstage control pressure defined. If there is no interstage control pressure defined in [COMPRESSOR_TRAIN_MODEL](/about/references/COMPRESSOR_TRAIN_MODEL.md),
[INTERSTAGE_CONTROL_PRESSURE](/about/references/INTERSTAGE_CONTROL_PRESSURE.md) should not be defined.