---
title: Facility inputs
sidebar_position: 2
description: Guide on how to use facility inputs
---

:::note
The [FACILITY_INPUTS](/about/references/FACILITY_INPUTS.md) keyword is **mandatory** within the eCalc™ YAML file.
:::

This part of the setup defines input files that characterize various facility elements. Each facility element is
specified in a list. These are later used as input in the [INSTALLATIONS](/about/references/INSTALLATIONS.md) part of the setup by referencing their [NAME](/about/references/NAME.md). 

All facility inputs are in essence a `CSV` (Comma separated file) file that specifies input data to a model that
calculates how much energy the equipment is using depending on the operating mode/throughput. There are multiple
[supported types](#supported-types).

There are four categories of data that can be used here:
- Files describing the performance of a [generator set](/about/modelling/setup/facility_inputs/generator_modelling.md)
- Files describing the performance of pumps [(pump charts)](/about/modelling/setup/facility_inputs/pump_modelling/pump_charts.md)
- Files describing the performance of **only** tabular compressors [(sampled compressor data)](/about/modelling/setup/facility_inputs/sampled_compressor_model.md)
- Other energy consuming equipment modeled variable w.r.t. reservoir management
  (tabulated relationship between variables and consumption)

eCalc™ supports making simple adjustments to a table by using the [ADJUSTMENT](/about/references/ADJUSTMENT.md)
keyword as well as modification of the [HEAD_MARGIN](/about/references/HEAD_MARGIN.md)
which can be used while calibrating pump charts.

## Format 

Each facility input has the skeleton as seen below. However, some inputs require further information. For example, [pump models](/about/modelling/setup/facility_inputs/pump_modelling/pump_charts.md)

~~~~yaml
FACILITY_INPUTS:
  - NAME: <reference name>
    FILE: <file_path.csv>
    TYPE: <consumer type>
~~~~

### Supported types
The facility input type is defined using the [TYPE](/about/references/TYPE.md) keyword and defines the type of model applied
to the data in this file. The input files are in `CSV` (Comma separated file) format. The paths to the input files may be either absolute or relative to the setup file.

The supported types are:

- `ELECTRICITY2FUEL`
- `TABULAR`
- `COMPRESSOR_TABULAR`
- `PUMP_CHART_SINGLE_SPEED`
- `PUMP_CHART_VARIABLE_SPEED`