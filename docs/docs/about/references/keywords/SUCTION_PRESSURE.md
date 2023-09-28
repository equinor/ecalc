# SUCTION_PRESSURE
 
[INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) /
[...] /
[ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md)  /
[...] /
[SUCTION_PRESSURE](/about/references/keywords/SUCTION_PRESSURE.md)

## Description
Used to define the suction pressure for some [ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md)
types and in [OPERATIONAL_SETTINGS](/about/references/keywords/OPERATIONAL_SETTINGS.md) using
a fixed value or an expression. If an expression is used, a time series can be used so that the suction pressure of the unit can vary over the lifespan of the model. 

Note that pressure values **must** be inputted in `bar`.

## Format
~~~~~~~~yaml
SUCTION_PRESSURE: <suction pressure value/expression>
~~~~~~~~

## Example
~~~~~~~~yaml
SUCTION_PRESSURE: 10 
~~~~~~~~