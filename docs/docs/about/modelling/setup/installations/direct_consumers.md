---
title: Direct consumers
sidebar_position: 7
---

# DIRECT ENERGY USAGE MODEL

This energy model usage type allows for defining energy usage directly with an expression. It needs to be either
accompanied by [LOAD](/about/references/LOAD.md) (for electrical consumers) or [FUELRATE](/about/references/FUELRATE.md) (for fuel consumers). The energy usage will be
equal to the result of the expression given for `LOAD`/`FUELRATE`.

When a model is run with [REGULARITY](/about/references/REGULARITY.md), there is an option to specify whether the direct consumer is of stream day
or calendar day energy usage rate with [CONSUMPTION_RATE_TYPE](/about/references/CONSUMPTION_RATE_TYPE.md).

#### Format

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: DIRECT
  LOAD/FUELRATE: <choose either load or fuelrate>
  CONSUMPTION_RATE_TYPE: <consumption rate type>
  CONDITION/S: <choose either condition or conditions>
  POWERLOSSFACTOR: <power loss factor (number)>
~~~~~~~~

#### Example

**Direct load**

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: DIRECT
  LOAD: 10 
~~~~~~~~

**Direct fuel rate**

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: DIRECT
  FUELRATE: 100000 
~~~~~~~~