---
sidebar_position: 7
description: Turbine modelling
---
# TURBINE
[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md): 
[TURBINE](/about/references/keywords_tree/MODELS/TYPE/TURBINE/index.md)

## Description
The turbine model requires values for efficiencies vs corresponding loads. Currently also a lower heating value needs to
be specified (planned feature is to get this from the fuel type used)

[TURBINE_LOADS](/about/references/keywords_tree/MODELS/TYPE/TURBINE/TURBINE_LOADS.md), 
[TURBINE_EFFICIENCIES](/about/references/keywords_tree/MODELS/TYPE/TURBINE/TURBINE_EFFICIENCIES.md) 
and [LOWER_HEATING_VALUE](/about/references/keywords_tree/MODELS/TYPE/TURBINE/LOWER_HEATING_VALUE.md) 
are required attributes for the `TURBINE` keyword.

The load values are given in MW, while efficiency values are numbers between 0 and 1.

The fuel usage for a turbine is equal to

$$
FUEL\_USAGE = \frac{LOAD\_IN\_MEGAWATT * SECONDS\_PER\_DAY}{LOWER\_HEATING\_VALUE * EFFICIENCY}
$$

When evaluated for a load (in units MW), the efficiency is evaluated by linearly interpolating the input load vs
efficiency data.

The input values for load and efficiency are lists which both MUST START WITH 0! The user is thus responsible for the
behaviour also for small load values.

For load values equal to 0, the fuel usage is also set to 0.

Lower heating value is given in units *MJ/Sm<sup>3</sup>*

## Format
~~~~~~~~yaml
MODELS:
  - NAME: <name of turbine>
    TYPE: TURBINE
    LOWER_HEATING_VALUE: <lower heating value in MJ/Sm3>
    TURBINE_LOADS: <list of power values in mega watt>
    TURBINE_EFFICIENCIES: <list of efficiency values, fractions between 0 and 1 corresponding to 0-100%>
    POWER_ADJUSTMENT_CONSTANT: <Optional constant MW adjustment added to the model>
~~~~~~~~

## Example
~~~~~~~~yaml
MODELS:
  - NAME: compressor_train_turbine
    TYPE: TURBINE
    LOWER_HEATING_VALUE: 38 # MJ/Sm3
    TURBINE_LOADS: [0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767] # MW
    TURBINE_EFFICIENCIES: [0, 0.138, 0.210, 0.255, 0.286, 0.310, 0.328, 0.342, 0.353, 0.360, 0.362]
    POWER_ADJUSTMENT_CONSTANT: 10
~~~~~~~~
