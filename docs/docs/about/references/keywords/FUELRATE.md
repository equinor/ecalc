# FUELRATE

[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md)
 /
[...] /
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) /
[FUELRATE](/about/references/keywords/FUELRATE.md)

## Description
Used for direct fuel `energy usage models<ENERGY_USAGE_MODEL>` to define fuel consumption directly with an
`expression <Expressions>`

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


