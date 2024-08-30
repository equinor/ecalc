# FUELRATE

[INSTALLATIONS](/about/references/INSTALLATIONS.md)
 /
[...] /
[ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) /
[FUELRATE](/about/references/FUELRATE.md)

## Description
Used for direct fuel [ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) to define fuel consumption directly with an
[EXPRESSION](/about/references/EXPRESSION.md).

## Format
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: DIRECT
  FUELRATE: <fuel rate expression [m3/day]>
  CONSUMPTION_RATE_TYPE: <consumption rate type>
  CONDITION: <condition expression>
~~~~~~~~

## Example

Constant fuel rate:
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: DIRECT
  FUELRATE: 100000  # [m3/day]
~~~~~~~~

Fuel rate varying in time:
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: DIRECT
  FUELRATE: fueldata;FUEL_RATE  # [m3/day]
~~~~~~~~


