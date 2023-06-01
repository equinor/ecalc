---
title: Generator sets
sidebar_position: 1
description: Using generator sets in calculations
---

# Generator sets in calculations

The [GENERATORSETS](../../../references/keywords/GENERATORSETS.md) keyword is optional. However, the only requirement is that each
installation must have defined either [GENERATORSETS](../../../references/keywords/GENERATORSETS.md) or
[FUELCONSUMERS](../../../references/keywords/FUELCONSUMERS.md).

Under [GENERATORSETS](../../../references/keywords/GENERATORSETS.md) one or several `generator sets` 
(a 'set' of an engine of some sort and a generator) are specified in a list.

Each generator set requires three sub-keywords, [ELECTRICITY2FUEL](../../../references/keywords/ELECTRICITY2FUEL)
and [CONSUMERS](../../../references/keywords/CONSUMERS) and [CATEGORY](../../../references/keywords/CATEGORY).
Optionally, [FUEL](../../../references/keywords/FUEL) may be used to override the default fuel type specification for
the installation. If not specified, it will inherit that of the installation.

:::tip What happens when fuel is specified?
When [FUEL](../../../references/keywords/FUEL) is defined for a generator set, there is no merging between the installation fuel
definition and the generator set fuel definition, but a complete override of the configuration.
:::

Category can be either `TURBINE-GENERATOR` or `POWER-FROM-SHORE`.

### Format
~~~~~~~~yaml
GENERATORSETS:
  - NAME: <generatorset name>
    CATEGORY: <category>
    FUEL: <optional fuel configuration reference>
    ELECTRICITY2FUEL: <electricity to fuel facility input reference>
    CONSUMERS:
      ...
~~~~~~~~

## Electricity2fuel function
### Description
The behavior of a generator set is described by an [ELECTRICITY2FUEL](../../../references/keywords/ELECTRICITY2FUEL)
table, which relates the burned fuel rate to delivered power, including the power generation efficiency at different loads.
It also defines the operational envelope of the generator set.

[ELECTRICITY2FUEL](../../../references/keywords/ELECTRICITY2FUEL) may be modeled with a constant function through time or
with different power vs. fuel relations for different time intervals.

### Format
~~~~~~~~yaml
ELECTRICITY2FUEL: <facility_input_reference>
~~~~~~~~

or

~~~~~~~~yaml
ELECTRICITY2FUEL:
  <DATE>: <facility_input_reference_1>
  <DATE>: <facility_input_reference_2>
~~~~~~~~

## Power from shore
### Description
:::note
Power from shore is currently handled in eCalc™ by defining a dummy [ELECTRICITY2FUEL](../../../references/keywords/ELECTRICITY2FUEL) model with zero fuel usage, and applying the `POWER-FROM-SHORE` category. This is an intermediate solution and will be dealt with differently in the future.
:::
### Example
Make an [ELECTRICITY2FUEL](../../../references/keywords/ELECTRICITY2FUEL) input file with zero fuel usage.

~~~~~~~~text
POWER, FUEL
# [MW], [SM3/day]
0, 0
50, 0
~~~~~~~~

Specify [ELECTRICITY2FUEL](../../../references/keywords/ELECTRICITY2FUEL) under 
[FACILITY_INPUTS](../../../references/keywords/FACILITY_INPUTS).

~~~~~~~~yaml
FACILITY_INPUTS:
 - NAME: genset_pfs
   TYPE: ELECTRICITY2FUEL
   FILE: genset_pfs.csv
~~~~~~~~

Use the `POWER-FROM-SHORE` category and the [ELECTRICITY2FUEL](../../../references/keywords/ELECTRICITY2FUEL) 
specified under [FACILITY_INPUTS](../../../references/keywords/FACILITY_INPUTS).

~~~~~~~~yaml
GENERATORSETS:
  - NAME: generatorset_with_pfs_event
    CATEGORY:
      2020-01-01: TURBINE-GENERATOR
      2030-01-01: POWER-FROM-SHORE
    ELECTRICITY2FUEL:
      2020-01-01: genset_turbine
      2030-01-01: genset_pfs
    CONSUMERS:
      ...
~~~~~~~~

If power from shore is used for the full time range you can skip the dates in both CATEGORY and ELECTRICITY2FUEL

~~~~~~~~yaml
GENERATORSETS:
  - NAME: generatorset_with_pfs_event
    CATEGORY: POWER-FROM-SHORE
    ELECTRICITY2FUEL: genset_pfs
    CONSUMERS:
      ...
~~~~~~~~

## Heaters and boilers
### Description
:::note
Heaters and boilers should be modeled in eCalc™ as 
[GENERATORSETS](../../../references/keywords/GENERATORSETS) or [FUELCONSUMERS](../../../references/keywords/FUELCONSUMERS), applying the [HEATER](../../../references/keywords/CATEGORY) and [BOILER](../../../references/keywords/CATEGORY) categories. This is an intermediate solution and may be dealt with differently in the future.
:::

### Example: Boiler as generator set
Specify the correlation between electric power delivered and fuel consumed under 
[FACILITY_INPUTS](../../../references/keywords/FACILITY_INPUTS):
~~~~~~~~yaml
FACILITY_INPUTS:
 - NAME: boiler_power_fuel
   TYPE: ELECTRICITY2FUEL
   FILE: boiler_power_fuel.csv
~~~~~~~~

Use the `BOILER` category and the [ELECTRICITY2FUEL](../../../references/keywords/ELECTRICITY2FUEL) 
specified under [FACILITY_INPUTS](../../../references/keywords/FACILITY_INPUTS):

~~~~~~~~yaml
GENERATORSETS:
  - NAME: boiler_as_generator
    CATEGORY: BOILER
    ELECTRICITY2FUEL: boiler_power_fuel
    CONSUMERS:
      ...
~~~~~~~~

### Example: Heater as fuel consumer
Specify the heater as a fuel consumer with category `HEATER`:

~~~~~~~~yaml
FUELCONSUMERS:
  - NAME: heater
    CATEGORY: HEATER
    ENERGY_USAGE_MODEL:
      TYPE: DIRECT
      FUELRATE: 100000
        ...
~~~~~~~~
