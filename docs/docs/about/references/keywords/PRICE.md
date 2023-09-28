# PRICE
 
[FUEL_TYPES](/about/references/keywords/FUEL_TYPES.md) / 
[PRICE](/about/references/keywords/PRICE.md)

## Description
The fuel [PRICE](/about/references/keywords/PRICE.md) defines the fuel cost (or the sales value of produced gas used as fuel).
The unit of the price is NOK/Sm<sup>3</sup>. [PRICE](/about/references/keywords/PRICE.md) can either be a fixed number or an expression (time series). Thus, it can be decided if a constant price or a price varying with time is needed.

## Format
~~~~~~~~yaml
FUEL_TYPES:
  - NAME: <name>
    PRICE: <price>
~~~~~~~~

## Example

### Fixed price

~~~~~~~~yaml
FUEL_TYPES:
  - NAME: diesel
    PRICE: 9000 # NOK/Sm3
~~~~~~~~

### Variable price

By making use of `Expressions`, you can model a varying fuel price through time:

~~~~~~~~yaml
EMISSIONS:
  - NAME: CO2
    FACTOR: 2.5 # kg/Sm3
    TAX: FUEL_PRICE_FILENAME;FUEL_PRICE
    QUOTA: 240 # NOK/ton CO2
~~~~~~~~

where the file `FUEL_PRICE_FILENAME.csv` could have the following content:

~~~~~~~~yaml
DATE,           FUEL_PRICE
01.01.2017,     9000
01.01.2018,     9500
01.01.2019,     9300
01.01.2020,     9800
01.01.2021,     9900
01.01.2022,     10000
01.01.2023,     10500
~~~~~~~~

Make sure the file [TYPE](/about/references/keywords/TYPE.md) is set to `FUEL_PRICE` to have a default `RIGHT`
[INTERPOLATION_TYPE](/about/references/keywords/INTERPOLATION_TYPE.md).
