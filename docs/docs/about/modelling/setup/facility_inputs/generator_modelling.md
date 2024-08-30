---
sidebar_position: 1
description: Generator modelling
---
# Generator modelling

In eCalc™, the term *generator* refers to equipment producing **electrical power from fuel**. Hence, the turbine part (fuel combustion to produce mechanical energy) is included in the term.

An installation usually have one or more generators to fill the electrical power demand. In eCalc™, the separate generators are combined into a common generator set (genset).

:::note
In the future, eCalc™ will most likely offer modelling of single generators that could be combined in systems.
:::

## ELECTRICITY2FUEL

Electricity to fuel is a table specifying the relationship between electrical load
and fuel consumption for an entire generator set. This means that if you have several generators,
this table needs to include a "jump" every time a new generator is started. An example of this
is shown [below](#table-example).

Under [FACILITY_INPUTS](/about/modelling/setup/facility_inputs/index.md), this electricity to fuel table is specified using the keyword [ELECTRICITY2FUEL](/about/references/ELECTRICITY2FUEL.md)

### Facility input format

~~~~yaml
FACILITY_INPUTS:
  - NAME: <generator name>
    FILE: <file path to .csv file>
    TYPE: ELECTRICITY2FUEL
~~~~

### Example table {#table-example}
The table for this curve would look like:

~~~~~~~~text
POWER, FUEL
#[MW], [Sm3/day]
0.00,  0.0
0.10,  84000.0
5.00,  84000.0
42.0,  220000.0
42.01, 280000.0
45.0,  300000.0
50.0,  330000.0
60.0,  350000.0
~~~~~~~~

### Header and unit requirements

| Header | Unit| Mandatory |
| ----- | ----| --- |
| Power | MW | Yes|
| Fuel  |  Sm<sup>3</sup>/day| Yes|