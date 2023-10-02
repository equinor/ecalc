---
title: Pump models
sidebar_position: 2
description: Using pumps in calculations
---

# Pump models in calculations
Pump charts are defined in the [FACILITY_INPUTS](/about/modelling/setup/facility_inputs/index.md) section, and is then referred to from an
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md).

## PUMP energy usage model
To configure a single pump, the pump rate, suction- and discharge pressures and fluid density must be given as inputs. In addition, a reference to a pump chart defined in the
[FACILITY_INPUTS](/about/modelling/setup/facility_inputs/pump_modelling/pump_charts.md) section has to be included.

### Format
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: PUMP
  CONDITION: <condition expression>
  ENERGYFUNCTION: <reference energy function in facility inputs of pump type>
  RATE: <rate expression>
  SUCTION_PRESSURE: <suction pressure expression>
  DISCHARGE_PRESSURE: <discharge pressure expression>
  FLUID_DENSITY: <fluid density expression>
~~~~~~~~

### Example
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: PUMP
  ENERGYFUNCTION: waterinjection_pump_reference
  RATE: SIM1;WATER_INJ
  SUCTION_PRESSURE: 3
  DISCHARGE_PRESSURE: 200
  FLUID_DENSITY: 1000
~~~~~~~~

### Units

| Quantity           | Default units      |
|--------------------|--------------------|
| RATE               | Sm<sup>3</sup>/day |
| SUCTION_PRESSURE   | bara                |
| DISCHARGE_PRESSURE | bara               |
| FLUID_DENSITY      | kg/m<sup>3</sup>   |


## PUMP_SYSTEM energy usage model

Model a system of pumps that share common manifolds and have cross-overs between them and for which the rate may be
split between them based on various operational strategies.

### Format
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: PUMP_SYSTEM
  CONDITION: <condition expression>
  PUMPS:
    - NAME: <name of compressor>
      CHART: <reference to pump model in facility inputs>
  TOTAL_SYSTEM_RATE: <expression defining the total rate in the system>
  FLUID_DENSITY: <expression defining the fluid density>
  OPERATIONAL_SETTINGS:
    <operational settings data>
~~~~~~~~

:::warning
 If all `OPERATIONAL_SETTINGS` have been exhausted, and there were still some time steps that were outside the
 capacity of the operational setting, the last operational setting will be "chosen" nevertheless. In this case the
 `energy_usage` in the output will be set to `NaN` which indicates that the operational setting, is in fact, invalid
 (or converted to 0 when aggregating upwards to e.g. genset)
:::

### Example

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: PUMP_SYSTEM
  PUMPS:
    - NAME: pump1
      CHART: water_injection_pump_reference
    - NAME: pump2
      CHART: water_injection_pump_reference
  TOTAL_SYSTEM_RATE: SIM1;WATER_INJ
  FLUID_DENSITY: 1000.0
  OPERATIONAL_SETTINGS:
    - RATE_FRACTIONS: [1, 0]
      SUCTION_PRESSURE: 3
      DISCHARGE_PRESSURE: 200
    - RATE_FRACTIONS: [0.5, 0.5]
      SUCTION_PRESSURE: 3
      DISCHARGE_PRESSURE: 200
~~~~~~~~

### Units

| Quantity           | Default units      |
|--------------------|--------------------|
| RATE               | Sm<sup>3</sup>/day |
| SUCTION_PRESSURE   | bara                |
| DISCHARGE_PRESSURE | bara               |
| FLUID_DENSITY      | kg/m<sup>3</sup>   |