---
title: Fuel types
sidebar_position: 4
description: Guide on how to use fuel types
---

:::note
The [FUEL_TYPES](/about/references/FUEL_TYPES.md) keyword is **mandatory** within the eCalc™ YAML file.
:::

This part of the setup specifies the various fuel types and associated emissions
used in the model. Each fuel type is specified in a list and the defined fuels can later be referred to the 
[INSTALLATIONS](/about/modelling/setup/installations/index.md) part of the setup by its name.

The use of fuel can lead to one or more emission types, specified in [EMISSIONS](/about/references/EMISSIONS.md).

You can optionally specify a [CATEGORY](/about/references/CATEGORY.md).

## Format
~~~~~~~~yaml
FUEL_TYPES:
  - NAME: <name_1>
    CATEGORY: <category_1>
    EMISSIONS: <emissions data>
  - NAME: <name_2>
    CATEGORY: <category_2>
    EMISSIONS: <emissions data>
~~~~~~~~

## Example
This is a full example where there are 3 fuel type definitions, i.e., there are 3 different
fuels defined that can be used in your [INSTALLATIONS](/about/modelling/setup/installations/index.md).

~~~~~~~~yaml
FUEL_TYPES:
  - NAME: fuel_gas # Name of this fuel, use this when referencing this fuel in the FUEL specification in the INSTALLATIONS part
    EMISSIONS:
      - NAME: CO2  # Name of the emission type
        FACTOR: 2.15 # kg/Sm3
      - NAME: CH4
        FACTOR: 0.00091 # kg/Sm3
  - NAME: flare_gas
    CATEGORY: FUEL_GAS
    EMISSIONS:
      - NAME: CO2
        FACTOR: 2.73
      - NAME: CH4
        FACTOR: 0.00024
  - NAME: diesel
    CATEGORY: DIESEL
    EMISSIONS:
      - NAME: CO2
        FACTOR: 2.7085 # kg/l - input diesel usage in l/d
~~~~~~~~

