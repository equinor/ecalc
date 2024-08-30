---
sidebar_position: 4
description: Turbine modelling
---
# Turbine modelling
The turbine model requires values for efficiencies vs corresponding loads. Currently also a lower heating value needs to
be specified (planned feature is to get this from the fuel type used)

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

### Combining a compressor train and a turbine into one model
To model a turbine driven compressor train, a compressor train model needs to be combined with a turbine model. The
calculated shaft power required for the compressor train, will then be the input of the turbine model to calculate
fuel usage.

## Format
~~~~~~~~yaml
MODELS:
  - NAME: <name of turbine model, for reference>
    TYPE: COMPRESSOR_WITH_TURBINE
    COMPRESSOR_MODEL: <reference to compressor train model defined in [MODELS](../references/MODELS) or [FACILITY_INPUTS](../references/FACILITY_INPUTS) (of type COMPRESSOR_TABULAR)>
    TURBINE_MODEL: <reference to a turbine model defined in [MODELS](../references/MODELS) (of type TURBINE)>
    POWER_ADJUSTMENT_CONSTANT: <Optional constant MW adjustment added to the model>
~~~~~~~~

## Examples
~~~~~~~~yaml
MODELS:
  - NAME: simplified_compressor_train_model_with_turbine
    TYPE: COMPRESSOR_WITH_TURBINE
    COMPRESSOR_MODEL: simplified_compressor_train_model
    TURBINE_MODEL: compressor_train_turbine
    POWER_ADJUSTMENT_CONSTANT: 10
~~~~~~~~

Turbine combined with presampled compressor model (`COMPRESSOR_TABULAR<COMPRESSOR_TABULAR  facility input type>`)

~~~~~~~~yaml
MODELS:
  - NAME: compressor_sampled_tabulated_model_with_turbine
    TYPE: COMPRESSOR_WITH_TURBINE
    COMPRESSOR_MODEL: compressor_sampled_tabulated_model
    TURBINE_MODEL: compressor_train_turbine
    POWER_ADJUSTMENT_CONSTANT: 10
~~~~~~~~

