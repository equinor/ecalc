---
sidebar_position: 2
---
# TURBINE_EFFICIENCIES

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md): 
[TURBINE](/about/references/keywords_tree/MODELS/TYPE/TURBINE/index.md) /
[TURBINE_EFFICIENCIES](/about/references/keywords_tree/MODELS/TYPE/TURBINE/TURBINE_EFFICIENCIES.md)

## Description

`TURBINE_EFFICIENCIES` is a required to be specified under the [TURBINE](/about/references/keywords_tree/MODELS/TYPE/TURBINE/index.md) keyword.

This **must** be specified as a fraction and **must** have equal length to the corresponding `TURBINE_LOAD` values.

## Format

~~~~yaml
MODELS:
  - NAME: <name of turbine>
    TYPE: TURBINE
    ...
    TURBINE_EFFICIENCIES: <list of efficiency values, fractions between 0 and 1 corresponding to 0-100%>
~~~~

## Example

~~~~yaml
MODELS:
  - NAME: compressor_train_turbine
    TYPE: TURBINE
    LOWER_HEATING_VALUE: 38 # MJ/Sm3
    TURBINE_LOADS: [0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767] # MW
    TURBINE_EFFICIENCIES: [0, 0.138, 0.210, 0.255, 0.286, 0.310, 0.328, 0.342, 0.353, 0.360, 0.362]
    POWER_ADJUSTMENT_CONSTANT: 10
~~~~
