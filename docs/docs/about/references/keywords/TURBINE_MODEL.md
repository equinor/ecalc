# TURBINE_MODEL

## Description

When using a [TURBINE](/about/modelling/setup/models/turbine_modeling.md) it is required for a `TURBINE_MODEL` to be specified. This is done under the `MODELS` section.

A turbine model describes a gas-fired turbine that is coupled to a compressor or compression train. It is specified in a similar way to a [GENERATORSET](GENERATORSETS.md). `TURBINE_LOAD`, `TURBINE_EFFICIENCY` and `LOWER_HEATING_VALUE` needs to be inputted here.

## Format

~~~~yaml
MODELS:
  - NAME: <name of turbine>
    TYPE: TURBINE
    LOWER_HEATING_VALUE: <lower heating value in MJ/Sm3>
    TURBINE_LOADS: <list of power values in mega watt>
    TURBINE_EFFICIENCIES: <list of efficiency values, fractions between 0 and 1 corresponding to 0-100%>
    POWER_ADJUSTMENT_CONSTANT: <Optional constant MW adjustment added to the model>
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
