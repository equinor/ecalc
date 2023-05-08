---
title: Variable speed compressor train multiple streams and pressures
sidebar_position: 3
description: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES Energy Usage Model
---

# VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES energy usage model

This energy usage model allows the compressor train model type 
[Variable speed compressor train model with multiple streams and pressures](../../models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures).

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
  POWER_ADJUSTMENT_CONSTANT: <Optional constant MW adjustment added to the model>
~~~~~~~~

The number of elements in [RATE_PER_STREAM](../../../../references/keywords/RATE_PER_STREAM) must correspond to the number of streams defined for the model referenced in
[COMPRESSOR_TRAIN_MODEL](../../../../references/keywords/COMPRESSOR_TRAIN_MODEL).

[INTERSTAGE_CONTROL_PRESSURE](../../../../references/keywords/INTERSTAGE_CONTROL_PRESSURE) is required if the model referenced in [COMPRESSOR_TRAIN_MODEL](../../../../references/keywords/COMPRESSOR_TRAIN_MODEL) has has an
interstage control pressure defined. If there is no interstage control pressure defined in [COMPRESSOR_TRAIN_MODEL](../../../../references/keywords/COMPRESSOR_TRAIN_MODEL),
[INTERSTAGE_CONTROL_PRESSURE](../../../../references/keywords/INTERSTAGE_CONTROL_PRESSURE) should not be defined.