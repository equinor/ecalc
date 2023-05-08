# EMISSIONS
 
[FUEL_TYPES](FUEL_TYPES) / 
[EMISSIONS](EMISSIONS.md)



| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| No         | `FUEL_TYPES`         | `FACTOR`  <br />  `NAME`     <br /> `QUOTA`   <br />    `TAX`        |


## Description
In [EMISSIONS](EMISSIONS.md) one or more emissions related to the use of fuel is specified as
a list. Each emission entry is **required** to have a [NAME](NAME) and a [FACTOR](FACTOR).

The costs associated with emitting typically have two cost elements:

- a quota price [NOK/ton] (based on emission mass) and,
- a tax price [NOK/Sm<sup>3</sup>] based on fuel gas volume.

The names  and  are chosen due to the  CO<sub>2</sub> emissions quota price (based on CO<sub>2</sub> mass) and
the Norwegian CO<sub>2</sub> tax

In general,  will be multiplied with the calculated emission volume while 
will be multiplied with the calculated fuel volume to obtain the resulting taxation.

The economical parameters are optional.

## Format
~~~~~~~~yaml
EMISSIONS:
  - NAME: <name>
    FACTOR: <factor>
    TAX: <expression>
    QUOTA: <expression>
~~~~~~~~

## Example
For example, if you want to add CO<sub>2</sub> emissions associated to the usage of a [FUEL_TYPES](FUEL_TYPES)
you write the following:

~~~~~~~~yaml
EMISSIONS:
  - NAME: CO2
    FACTOR: 2.5  # [kg/Sm3]
    TAX: 1.5  # [NOK/Sm3]
    QUOTA: 240  # NOK/ton CO2
~~~~~~~~

