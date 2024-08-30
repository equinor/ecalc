---
title: Time series
sidebar_position: 2
description: Time series guide and description
---

:::note
The [TIME_SERIES](/about/references/TIME_SERIES.md) keyword is **mandatory** within the eCalc™ YAML file.
:::

This part of the setup file defines the inputs for time dependent variables, or "reservoir
variables". For many fields, this may be only one reservoir simulation model. But in some
cases, one might have several sources for reservoir and other relevant time series variables.

For example, a field may have a reservoir simulation model for some areas and decline curves in other area of
the reservoir. There may also be tie-ins which are affecting the energy/emissions on the field
installations. Also, there may be time profiles for other variables.
Therefore, a set of sources may be specified with a name, path to data and type. The name is
later referred to in the system of energy consumers defined under [INSTALLATIONS](/about/references/INSTALLATIONS.md).

Reservoir variables and other time varying data not coming from a reservoir simulation model can
be specified in a [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) file.

The paths to the input files may be either absolute or relative to the setup file.

## Supported types

The supported time series types are:

| Type          | Supported file formats  | Interpolation type                                              | Comment                                                                                                    |
|---------------|-------------------------|-----------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| DEFAULT       | .csv                    | Not possible to specify: <br />`RIGHT` is used  | **New in v8.1**                                                                                            |
| MISCELLANEOUS | .csv                    | Mandatory input:<br />`LEFT`/`RIGHT`/`LINEAR`                   |                                                                                                            |

## Format
Each line under [TIME_SERIES](/about/references/TIME_SERIES.md) has the format:

~~~~~~~~yaml
TIME_SERIES:
  - NAME: <time series reference name>
    TYPE: <type>
    FILE: <path_to_file>
    INFLUENCE_TIME_VECTOR: <True/False>
    EXTRAPOLATION: <True/False>
    INTERPOLATION_TYPE: <LEFT/RIGHT/LINEAR>
~~~~~~~~

The input data is expected to be in metric units. The [NAME](/about/references/NAME.md) is later referred
to in the [INSTALLATIONS](/about/references/INSTALLATIONS.md) part of the setup file.
[INFLUENCE_TIME_VECTOR](/about/references/INFLUENCE_TIME_VECTOR.md), [EXTRAPOLATION](/about/references/EXTRAPOLATION.md)
and [INTERPOLATION_TYPE](/about/references/INTERPOLATION_TYPE.md) may have default values set depending
on the choice of [TYPE](/about/references/TYPE.md). See the documentation for each keyword for details.

### Requirements
- At least one input source with [INFLUENCE_TIME_VECTOR](/about/references/INFLUENCE_TIME_VECTOR.md) set to True.
- Must include sources referred to in the variables for each consumer.

## Example
~~~~~~~~yaml
TIME_SERIES:
  - NAME: SIM1
    TYPE: DEFAULT
    FILE: /path_to_model1/model_data.csv
  - NAME: SIM2
    TYPE: DEFAULT
    FILE:  /path_to_tiein/tie_in_field.csv
  - NAME: DATA3
    TYPE: MISCELLANEOUS # e.g. variable flare, compressor suction and discharge pressures
    FILE: inputs/somecsvdata.csv
    INFLUENCE_TIME_VECTOR: FALSE
    EXTRAPOLATION: TRUE
    INTERPOLATION_TYPE: RIGHT
~~~~~~~~


