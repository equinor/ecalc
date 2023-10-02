# DISCHARGE_PRESSURE
 
[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) / 
[...] /
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md) /
[...] / [DISCHARGE_PRESSURE](/about/references/keywords/DISCHARGE_PRESSURE.md)

| Required   | Child of                   | Children/Options                   |
|------------|----------------------------|------------------------------------|
| Yes        | `ENERGY_USAGE_MODEL` <br /> `OPERATIONAL_SETTINGS` | None                               |


## Description
Used to define the discharge pressure for some [ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md)
 types  and in [OPERATIONAL_SETTINGS](/about/references/keywords/OPERATIONAL_SETTINGS.md) using an 
[Expressions](/about/references/keywords/EXPRESSION.md).

## Format
~~~~~~~~yaml
DISCHARGE_PRESSURE: <discharge pressure expression>
~~~~~~~~

## Example
~~~~~~~~yaml
DISCHARGE_PRESSURE: 200 # [bar]
~~~~~~~~

