---
title: Models
sidebar_position: 4
description: Guide on how to use models in eCalc™ 
---

:::note
The [MODELS](../../../references/keywords/MODELS) keyword is **optional** for an eCalc™ model to run. However, it is critical for compressor and turbine modelling.
:::

This part of the setup defines input files that characterize various fluid, compressor and turbine models. These are later used as input in the [INSTALLATIONS](../../../references/keywords/INSTALLATIONS) part of the setup by referencing their [NAME](../../../references/keywords/NAME).

## Format

~~~~~~~~yaml
MODELS:
  - NAME: <name of model, for reference>
    TYPE: <model type>
    <other keywords according to TYPE>
~~~~~~~~

## Supported types

The supported types are:

- `FLUID`
- `COMPRESSOR_CHART`
- `SINGLE_SPEED_COMPRESSOR_TRAIN`
- `SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN`
- `VARIABLE_SPEED_COMPRESSOR_TRAIN`
- `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`
- `TURBINE`
- `COMPRESSOR_WITH_TURBINE`
