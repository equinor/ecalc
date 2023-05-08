---
title: Tabular models
sidebar_position: 4
description: Using tabular models in calculations
---

This type is a pure interpolation model where the user may freely choose all the variables. No extrapolation is done, thus the user
must ensure to cover the entire variable space in the input data. For points outside the input data, the output is
invalid and no energy usage is given (shown in the output vector extrapolations).

## Format

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: TABULATED
  CONDITION: <condition expression>
  ENERGYFUNCTION: <reference to energy function in facility inputs of type tabular>
  VARIABLES:
    - NAME: <name of variable>
      EXPRESSION: <expression defining the variable>
~~~~~~~~

## Example

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: TABULATED
  ENERGYFUNCTION: tabulated_energy_function_reference
  VARIABLES:
    - NAME: RATE
      EXPRESSION: SIM1;GAS_PROD
    - NAME: Gas oil ratio
      EXPRESSION: SIM1;GOR
    - NAME: GAS_TEMPERATURE
      EXPRESSION: SIM1;TEMP
~~~~~~~~

## COMPRESSOR_TABULAR input type

Consumer energy function for the compressor (or compressor train) is in a tabulated format,
where each line is a point defining the energy consumption for the given variables.

See [Sampled compressor model](../facility_inputs/sampled_compressor_model) for details.

As a single compressor/compressor train (no system), it can be set up in the following way:

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: COMPRESSOR
  ENERGYFUNCTION: <facility_inputs_key>
  RATE: <rate expression [Sm3/day]>
  SUCTION_PRESSURE: <suction pressure expression>
  DISCHARGE_PRESSURE: <discharge pressure expression>
~~~~~~~~