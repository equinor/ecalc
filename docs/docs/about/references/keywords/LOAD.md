# LOAD

[INSTALLATIONS](INSTALLATIONS) /
[...] / 
[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL) / 
[LOAD](LOAD)

## Description
Used for direct load `energy usage models<ENERGY_USAGE_MODEL>` to define electrical power load directly
with an `expression <Expressions>`

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

