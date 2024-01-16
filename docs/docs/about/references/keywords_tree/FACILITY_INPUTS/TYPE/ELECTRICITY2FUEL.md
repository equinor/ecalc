---
sidebar_position: 1
---
# ELECTRICITY2FUEL
[FACILITY_INPUTS](/about/references/keywords_tree/FACILITY_INPUTS/index.md) /
[TYPE](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/index.md) :
[ELECTRICITY2FUEL](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/ELECTRICITY2FUEL.md)

Electricity to fuel is a table specifying the relationship between electrical load
and fuel consumption for an entire generator set. This means that if you have several generators,
this table needs to include a "jump" every time a new generator is started. An example of this
is shown [below](#Table-example).

Under [FACILITY_INPUTS](/about/modelling/setup/facility_inputs/index.md), this electricity to fuel table is specified using the keyword [ELECTRICITY2FUEL](/about/references/keywords/ELECTRICITY2FUEL.md)

### Facility input format

~~~~yaml
FACILITY_INPUTS:
  - NAME: <generator name>
    FILE: <file path to .csv file>
    TYPE: ELECTRICITY2FUEL
~~~~

### Example table
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