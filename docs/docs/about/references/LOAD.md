# LOAD

[INSTALLATIONS](/about/references/INSTALLATIONS.md) /
[...] / 
[ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) / 
[LOAD](/about/references/LOAD.md)

## Description
Used for direct load [ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) to define electrical power load directly
with an [EXPRESSION](/about/references/EXPRESSION.md).

## Format
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: DIRECT
  LOAD: <load expression>
  CONSUMPTION_RATE_TYPE: <consumption rate type>
  CONDITION: <condition expression>
  POWERLOSSFACTOR: <power loss factor (number)>
~~~~~~~~

## Example
~~~~~~~~yaml
ENERGY_USAGE_MODEL:
  TYPE: DIRECT
  LOAD: 10
~~~~~~~~

