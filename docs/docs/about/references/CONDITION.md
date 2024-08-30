# CONDITION
 
[INSTALLATIONS](/about/references/INSTALLATIONS.md) /
[...] /
[ENERGY_USAGE_MODEL](/about/references/ENERGY_USAGE_MODEL.md) / 
[CONDITION](/about/references/CONDITION.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| No         | `ENERGY_USAGE_MODEL`      | None                               |

## Description
All energy usage models may have a keyword [CONDITION](/about/references/CONDITION.md)
 which specifies conditions for the  consumer to be used. At points in the time series where the condition
evaluates to `0` (or `False`), the energy consumption will be `0`.
This is practical for some otherwise
constant consumers.
For example, if you use the category `FIXED-PRODUCTION-LOAD` and you want it to depend on whether or not there is production, the `CONDITION` keyword can be specified.

`CONDITION` supports the functionality described in [Expressions](/about/references/EXPRESSION.md), but is **required** to evaluate to `True/False` or `1/0`.

## Format
~~~~~~~~yaml
CONDITION: <CONDITION>
~~~~~~~~

## Example
A simple example is shown below where the load is only present whenever the oil production is positive:

~~~~~~~~yaml
- NAME: production_load
  CATEGORY: FIXED-PRODUCTION-LOAD
  ENERGY_USAGE_MODEL:
    LOAD: 5
    CONDITION: SIM1;OIL_PROD:PLA > 0
~~~~~~~~

This condition is an expression. See [Expressions](/about/references/EXPRESSION.md).
