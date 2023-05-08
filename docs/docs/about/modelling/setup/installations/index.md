---
title: Installations
sidebar_position: 7
description: Guide on how to use installations
---

:::note
The [INSTALLATIONS](../../../references/keywords/INSTALLATIONS) keyword is **mandatory** within the eCalc™ YAML file.
:::

In [INSTALLATIONS](../../../references/keywords/INSTALLATIONS) the system of energy consumers is described. Installations, in this setting, are typically the different platforms and production units for a field, group of fields, or area. Mobile units (such as drilling rigs) are also modelled as an installation.

* Essentially installations on which fuel is burned to generate energy for the consumers.

The structure of the keywords under [INSTALLATIONS](../../../references/keywords/INSTALLATIONS)
is linked to the structure in the general consumer overview for an installation.

[CATEGORY](../../../references/keywords/CATEGORY) is optional, and generally reserved for use with LTP.

### Referring to time series
In the installations set up, one may refer to variables from [TIME_SERIES](../../../references/keywords/TIME_SERIES.md)
in many places by using `expressions` to build up custom, or changing, configurations.

Referring to variables is done on the format:

~~~~~~~~yaml
<KEY>;<VARIABLE_NAME>
~~~~~~~~

where `<KEY>` must be defined in [TIME_SERIES](../time_series), defining the time series input source
(e.g., CSV file), and `<VARIABLE_NAME>` is the name of the variable.
See [TIME SERIES](../time_series) for more examples

### Time intervals for variables/expressions and models

For various reasons, the data in the [INSTALLATIONS](../../../references/keywords/INSTALLATIONS) section may vary in time.
The consumers may need to be modeled differently due to rebuilds or degeneration. It could be that the user wants to
make a simple model for some periods and a more detailed model for others (e.g., a rate only model early time periods and a pressure
dependent model in the field's late life).

For the fields that support multiple time intervals, the syntax is generally to insert a
date on the format `YYYY-MM-DD` followed by the expression/model for the time interval between
this date and the next entered date. See `Time intervals` for an example.

:::note Note
When time dependency is used, the values before the first time default to 0 (zero)
:::

* [HCEXPORT](../../../references/keywords/HCEXPORT) is zero before the first time given.
* [ELECTRICITY2FUEL](../../../references/keywords/ELECTRICITY2FUEL) will have 0 fuel usage before the first time defined, despite a non-zero power load.
* [FUEL](../../../references/keywords/FUEL): The fuel rate will be 0 before the first entered date.
* Consumer energy consumption will be 0 before the first defined time.

## Format
~~~~~~~~yaml
INSTALLATIONS:
  - NAME: <name of installation 1>
    GENERATORSETS: <generator set specifications for installation 1>
    FUELCONSUMERS: <fuel consumer specifications for installation 1>
    FUEL: <fuel specification for installation 1>
    HCEXPORT: <hydrocarbon export specification for installation 1>
    REGULARITY: <regularity specification for installation 1>
    DIRECT_EMITTERS: <direct emissions specification for installation 1>
    CATEGORY: <category for installation 1>
  - NAME: <name of installation 2>
    GENERATORSETS: <generator set specifications for installation 2>
    FUELCONSUMERS: <fuel consumer specifications for installation 2>
    FUEL: <fuel specification for installation 2>
    HCEXPORT: <hydrocarbon export specification for installation 2>
    REGULARITY: <regularity specification for installation 2>
    DIRECT_EMITTERS: <direct emissions specification for installation 2>
    CATEGORY: <category for installation 2>
  - ...
~~~~~~~~

## Example
### General structure
~~~~~~~~yaml
INSTALLATIONS
  - NAME: Platform_A
    CATEGORY: FIXED
    <The data for installation 1 to be put here>
  - NAME: Platform_B
    CATEGORY: MOBILE
    <The data for installation 2 to be put here>
~~~~~~~~

### Referring to time series
~~~~~~~~yaml
SIM;OIL_PROD
~~~~~~~~

`SIM` is the key defined in [TIME_SERIES](../../../references/keywords/TIME_SERIES.md).

The user can define expressions of variables,
see `expressions` for details. The following is an example of using expressions:

~~~~~~~~yaml
SIM1;WATER_PROD:FIELD_A {+} SIM2;WATER_PROD:FIELD_B
~~~~~~~~

`SIM1` and `SIM2` are here different reservoir sources with potential different time steps.
This is not a problem and handled by eCalc automatically.

### Time intervals
This example uses the [HCEXPORT](../../../references/keywords/HCEXPORT) keyword.

**Example: same expression for the entire time frame**

~~~~~~~~yaml
HCEXPORT: SIM;OIL_PROD
~~~~~~~~

**Example: expression varies through time**

~~~~~~~~yaml
HCEXPORT:
  2001-01-01: SIM1;OIL_PROD
  2005-01-01: SIM2:OIL_PROD {+} SIM2;GAS_SALES
~~~~~~~~

