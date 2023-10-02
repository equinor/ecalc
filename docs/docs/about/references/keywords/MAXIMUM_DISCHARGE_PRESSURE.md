# MAXIMUM_DISCHARGE_PRESSURE

[MODELS](/about/references/keywords/MODELS.md) / 
[MAXIMUM_DISCHARGE_PRESSURE](/about/references/keywords/MAXIMUM_DISCHARGE_PRESSURE.md)

## Description

`MAXIMUM_DISCHARGE_PRESSURE` sets the highest possible discharge pressure that a compressor can deliver.
In reality, setting the maximum discharge pressure can be to avoid excessively high pressures which can be a safety concern on an installation.

## Functionality

This is an optional setting and is **only** supported for [SINGLE SPEED COMPRESSORS](/about/modelling/setup/models/compressor_modelling/compressor_models_types/single_speed_compressor_train_model.md), and **only** if the `PRESSURE_CONTROL` is `DOWNSTREAM_CHOKE`.

* If `MAXIMUM_DISCHARGE_PRESSURE` has been defined and if any of the inputted discharge pressures exceeds the maximum value, a ValueError message will be raised.
* If any of the input rates and suction pressures result in a discharge pressure which is above the `MAXIMUM_DISCHARGE_PRESSURE`, the suction pressure will be reduced until the calculations provide a discharge pressure below the maximum value (assuming an upstream choke can handle this).
* The outlet stream will then be further choked from the `MAXIMUM_DISCHARGE_PRESSURE` to the target discharge pressure using the `DOWNSTREAM_CHOKE` pressure control.

## Format

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: SINGLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: <reference to fluid model>
    PRESSURE_CONTROL: <DOWNSTREAM_CHOKE>
    MAXIMUM_DISCHARGE_PRESSURE: <Maximum discharge pressure in bar>
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
          COMPRESSOR_CHART: <reference to compressor chart model>
    ...
~~~~~~~~
