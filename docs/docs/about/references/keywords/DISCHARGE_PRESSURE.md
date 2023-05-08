# DISCHARGE_PRESSURE
 
[INSTALLATIONS](INSTALLATIONS) / 
[...] /
[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL) /
[...] / [DISCHARGE_PRESSURE](DISCHARGE_PRESSURE)

| Required   | Child of                   | Children/Options                   |
|------------|----------------------------|------------------------------------|
| Yes        | `ENERGY_USAGE_MODEL` <br /> `OPERATIONAL_SETTINGS` | None                               |


## Description
Used to define the discharge pressure for some [ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL)
 types  and in [OPERATIONAL_SETTINGS](OPERATIONAL_SETTINGS) using an 
[Expressions](EXPRESSION).

## Format
~~~~~~~~yaml
DISCHARGE_PRESSURE: <discharge pressure expression>
~~~~~~~~

## Example
~~~~~~~~yaml
DISCHARGE_PRESSURE: 200 # [bar]
~~~~~~~~

