---
title: Variables
sidebar_position: 6
description: Variables guide and description
---

:::note
The [VARIABLES](/about/references/VARIABLES.md) keyword is **optional** for an eCalc™ model to run.
:::

## Defining variables

Variables are defined in their own section in the YAML file, they can either be defined without link to time, or linked to time.

### Format

~~~~~~~~yaml
VARIABLES:
  <variable name>:
    VALUE: <expression>
~~~~~~~~

With time link: 

~~~~~~~~yaml
VARIABLES:
  <variable name>:
    <YYYY-MM-DD [HH:mm:ss]>:
      VALUE: <expression>
~~~~~~~~

### Examples
~~~~~~~~yaml
VARIABLES:
  salt_water_injection:
    VALUE: SIM1:COL1 {*} 2
~~~~~~~~

With time link: 
~~~~~~~~yaml
VARIABLES:
  salt_water_injection:
    2010-01-01:
      VALUE: SIM1:COL1 {*} 2
    2020-01-01:
      VALUE: SIM1:COL1
~~~~~~~~

## Using variables

Variables can be used in any expression throughout the YAML file and can even be used within defining other variables.

### Example 

Using variables in the [INSTALLATION](/about/modelling/setup/installations/index.md) section:

~~~~yaml
VARIABLES:
    gas_rateA:
        VALUE: SIM;COL1
    gas_rateB:
        VALUE: SIM;COL2

INSTALLATIONS: 
    - NAME: installationA
      CATEGORY: FIXED
        ...
            - NAME: sample_compressor
              CATEGORY: COMPRESSOR
              ENERGYFUNCTION: compressorA
              RATE: $var.gas_rateA {+} $var.gas_rateB
              ...
~~~~

Using variables in defining another variable:

~~~~~~~~yaml
VARIABLES:
  salt_water_injection:
    VALUE: SIM1:COL1 {*} 2
  double_injection_rate:
    VALUE: $var.salt_water_injection {*} 2
~~~~~~~~


