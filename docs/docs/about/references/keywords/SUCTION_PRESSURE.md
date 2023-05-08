# SUCTION_PRESSURE
 
[INSTALLATIONS](INSTALLATIONS) /
[...] /
[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL)  /
[...] /
[SUCTION_PRESSURE](SUCTION_PRESSURE)

## Description
Used to define the suction pressure for some [ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL)
types and in [OPERATIONAL_SETTINGS](OPERATIONAL_SETTINGS) using
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