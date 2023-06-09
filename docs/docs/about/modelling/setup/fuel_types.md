---
title: Fuel types
sidebar_position: 5
description: Guide on how to use fuel types
---

:::note
The [FUEL_TYPES](../../references/keywords/FUEL_TYPES) keyword is **mandatory** within the eCalc™ YAML file.
:::

This part of the setup specifies the various fuel types and associated emissions
used in the model. Each fuel type is specified in a list and the defined fuels can later be referred to the 
[INSTALLATIONS](installations/) part of the setup by its name.

A fuel type can have a fuel-cost [PRICE](../../references/keywords/PRICE) associated with
its use. The use of fuel can lead to one or more emission types, specified in [EMISSIONS](../../references/keywords/EMISSIONS.md),
which in turn can have associated costs.

You can optionally specify a [CATEGORY](../../references/keywords/CATEGORY).

## Format
~~~~~~~~yaml
FUEL_TYPES:
  - NAME: <name_1>
    CATEGORY: <category_1>
    PRICE: <fuel price>
    EMISSIONS: <emissions data>
  - NAME: <name_2>
    CATEGORY: <category_2>
    PRICE: <fuel price>
    EMISSIONS: <emissions data>
~~~~~~~~

## Example
This is a full example where there are 3 fuel type definitions, i.e., there are 3 different
fuels defined that can be used in your [INSTALLATIONS](installations/index.md).

~~~~~~~~yaml
FUEL_TYPES:
  - NAME: fuel_gas # Name of this fuel, use this when referencing this fuel in the FUEL specification in the INSTALLATIONS part
    PRICE: 1.5     # The price or sales value of the fuel
    EMISSIONS:
      - NAME: CO2  # Name of the emission type
        FACTOR: 2.15 # kg/Sm3
        TAX: 1.51  # NOK/Sm3
        QUOTA: 280 # NOK/ton
     - NAME: CH4
       FACTOR: 0.00091 # kg/Sm3
  - NAME: flare_gas
    PRICE: 1.5
    CATEGORY: FUEL_GAS
    EMISSIONS:
      - NAME: CO2
        FACTOR: 2.73
        TAX: 1.51
      - NAME: CH4
        FACTOR: 0.00024
  - NAME: diesel
    CATEGORY: DIESEL
    PRICE: 9000  # NOK/m3
    EMISSIONS:
      - NAME: CO2
        FACTOR: 2.7085 # kg/l - input diesel usage in l/d
~~~~~~~~

