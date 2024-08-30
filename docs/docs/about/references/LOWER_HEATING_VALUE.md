# LOWER_HEATING_VALUE

## Description

`LOWER_HEATING_VALUE` is a required to be specified under the [TURBINE_MODEL](/about/references/TURBINE_MODEL.md) keyword.
This **must** be specified in MJ/Sm<sup>3</sup>

This can only be inputted as a single value and dictates the quantity of thermal energy available after burning a standard cubic metre of fuel (natural gas in this gas).

## Format

~~~~yaml
MODELS:
  - NAME: <name of turbine>
    TYPE: TURBINE
    ...
    LOWER_HEATING_VALUE: <lower heating value in MJ/Sm3>
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
