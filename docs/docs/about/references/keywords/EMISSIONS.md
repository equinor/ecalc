# EMISSIONS
 
[FUEL_TYPES](/about/references/keywords/FUEL_TYPES.md) / 
[EMISSIONS](/about/references/keywords/EMISSIONS.md)



| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| No         | `FUEL_TYPES`         | `FACTOR`  <br />  `NAME`            |


## Description
In [EMISSIONS](/about/references/keywords/EMISSIONS.md) one or more emissions related to the use of fuel is specified as
a list. Each emission entry is **required** to have a [NAME](/about/references/keywords/NAME.md) and a [FACTOR](/about/references/keywords/FACTOR.mdx).


## Format
~~~~~~~~yaml
EMISSIONS:
  - NAME: <name>
    FACTOR: <factor>
~~~~~~~~

## Example
For example, if you want to add CO<sub>2</sub> emissions associated to the usage of a [FUEL_TYPES](/about/references/keywords/FUEL_TYPES.md)
you write the following:

~~~~~~~~yaml
EMISSIONS:
  - NAME: CO2
    FACTOR: 2.5  # [kg/Sm3]
~~~~~~~~

