---
sidebar_position: 2
---
# EMISSIONS
 
[FUEL_TYPES](/about/references/keywords_tree/FUEL_TYPES/index.md) / 
[EMISSIONS](/about/references/keywords_tree/FUEL_TYPES/EMISSIONS/index.md)



| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| No         | `FUEL_TYPES`         | `FACTOR`  <br />  `NAME`            |


## Description
In [EMISSIONS](/about/references/keywords_tree/FUEL_TYPES/EMISSIONS/index.md) one or more emissions related to the use of fuel is specified as
a list. Each emission entry is **required** to have a [NAME](/about/references/keywords_tree/FUEL_TYPES/EMISSIONS/NAME.md) 
and a [FACTOR](/about/references/keywords_tree/FUEL_TYPES/EMISSIONS/FACTOR.md).


## Format
~~~~~~~~yaml
EMISSIONS:
  - NAME: <name>
    FACTOR: <factor>
~~~~~~~~

## Example
For example, if you want to add CO<sub>2</sub> emissions associated to the usage of a [FUEL_TYPES](/about/references/keywords_tree/FUEL_TYPES/index.md)
you write the following:

~~~~~~~~yaml
EMISSIONS:
  - NAME: CO2
    FACTOR: 2.5  # [kg/Sm3]
~~~~~~~~

