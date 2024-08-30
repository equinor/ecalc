# DISCHARGE_PRESSURE
 
[INSTALLATIONS](/about/references/INSTALLATIONS.md) / 
[...] /
[ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) /
[...] / [DISCHARGE_PRESSURE](/about/references/DISCHARGE_PRESSURE.md)

| Required   | Child of                   | Children/Options                   |
|------------|----------------------------|------------------------------------|
| Yes        | `ENERGY_USAGE_MODEL` <br /> `OPERATIONAL_SETTINGS` | None                               |


## Description
Used to define the discharge pressure for some [ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md)
 types  and in [OPERATIONAL_SETTINGS](/about/references/OPERATIONAL_SETTINGS.md) using an 
[Expressions](/about/references/EXPRESSION.md).

## Format
~~~~~~~~yaml
DISCHARGE_PRESSURE: <discharge pressure expression>
~~~~~~~~

## Example
~~~~~~~~yaml
DISCHARGE_PRESSURE: 200 # [bar]
~~~~~~~~

