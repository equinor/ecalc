# TOTAL_SYSTEM_RATE
 
[INSTALLATIONS](/about/references/INSTALLATIONS.md) / [...] / 
[ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) / 
[TOTAL_SYSTEM_RATE](/about/references/TOTAL_SYSTEM_RATE.md)

## Description
Used to define the total system rate [Sm<sup>3</sup>/day] for `ENERGY_USAGE_MODEL` of type `COMPRESSOR_SYSTEM`
and `PUMP_SYSTEM`.

## Format
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: PUMP_SYSTEM
  TOTAL_SYSTEM_RATE: <expression defining the total rate in the system [Sm3/day]>
~~~~~~~~

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: COMPRESSOR_SYSTEM
  TOTAL_SYSTEM_RATE: <expression defining the total rate in the system>
~~~~~~~~

## Example
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: PUMP_SYSTEM
  TOTAL_SYSTEM_RATE: SIM1;WATER_INJ
~~~~~~~~

~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: COMPRESSOR_SYSTEM
  TOTAL_SYSTEM_RATE: SIM1;GAS_PROD {+} SIM1;GAS_LIFT
~~~~~~~~

