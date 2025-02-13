---
title: Models
sidebar_position: 3
description: Guide on how to use models in eCalc™ 
---

:::note
The [MODELS](/about/references/MODELS.md) keyword is **optional** for an eCalc™ model to run. However, it is critical for compressor and turbine modelling.
:::

This part of the setup defines input files that characterize various fluid, compressor and turbine models. These are later used as input in the [INSTALLATIONS](../../../references/INSTALLATIONS) part of the setup by referencing their [NAME](../../../references/NAME).

## Format

~~~~~~~~yaml
MODELS:
  - NAME: <name of model, for reference>
    TYPE: <model type>
    <other keywords according to TYPE>
~~~~~~~~

## Supported types

The supported types are:

- `FLUID` described in more detail in [Fluid model](/about/modelling/setup/models/fluid_model.md)
- `COMPRESSOR_CHART` described in more detail in [Compressor chart](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md)
- `SINGLE_SPEED_COMPRESSOR_TRAIN`
- `SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN`
- `VARIABLE_SPEED_COMPRESSOR_TRAIN`
- `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`
- `TURBINE`
- `COMPRESSOR_WITH_TURBINE`
